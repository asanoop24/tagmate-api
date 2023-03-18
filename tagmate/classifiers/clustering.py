import uuid
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from tagmate.models.db.activity import (
    Activity as ActivityTable,
    Document as DocumentTable,
    Cluster as ClusterTable,
)
from tagmate.utils.database import db_init
from tagmate.logging.worker import JobLogger


model_id = "all-MiniLM-L6-v2"


class ClusterBuilder:
    def __init__(self, activity_id: str, logger: JobLogger | None = None):
        self.activity_id = activity_id
        self.model_id = model_id
        self.logger = logger

    def load_model(self):
        self.model = SentenceTransformer(model_id)

    async def fetch_activity_from_db(self):
        self.activity = await ActivityTable.get(id=self.activity_id)

    async def fetch_activity_documents(self):
        min_sentence_len = 10
        self.documents = await DocumentTable.filter(activity_id=self.activity_id)
        # self.documents = [[doc.id, doc.text] for doc in self.documents]
        # self.texts = [doc[1] for doc in self.documents]
        # self.idx2id = {idx: doc[0] for idx, doc in enumerate(self.documents)}
        documents_list = [[doc.id, doc.text] for doc in self.documents]
        documents_df = pd.DataFrame(data=documents_list, columns=["id", "text"])
        documents_df["sentence"] = documents_df["text"].apply(lambda x: x.split("."))
        documents_df = documents_df.explode("sentence")
        documents_df["sentence"] = documents_df["sentence"].apply(lambda x: x.strip())
        documents_df = documents_df[documents_df["sentence"].str.len() > min_sentence_len].reset_index(drop=True)
        self.documents_df = documents_df.reset_index().rename(columns={"index": "sentence_idx"})
        self.sentences = documents_df["sentence"].tolist()
        self.logger.info(self.documents_df[:10])
        self.logger.info(self.sentences[:10])
        

    def generate_embeddings(self):
        self.embeddings = self.model.encode(
            self.sentences, batch_size=8, show_progress_bar=True, convert_to_tensor=True
        )
        self.logger.info(self.embeddings)

    def build_clusters(self, size=20):
        self.clusters = util.community_detection(
            self.embeddings, min_community_size=size, threshold=0.65
        )
        if len(self.clusters) == 0:
            self.logger.info(f"cluster count: {len(self.clusters)}")
            self.logger.info(f"cluster size: {size}")
            self.build_clusters(size=size//2)

    async def save_clusters(self):
        clusters_to_save = []
        sentence2cluster = {}
        for cluster_idx, cluster_sentences in enumerate(self.clusters):
            cluster_id = str(uuid.uuid4())
            clusters_to_save.append(
                ClusterTable(id=cluster_id, index=cluster_idx, theme="RandomTheme")
            )
            for sentence_idx in cluster_sentences:
                sentence2cluster[sentence_idx] = cluster_id
        
        self.documents_df["cluster_id"] = self.documents_df["sentence_idx"].apply(lambda x: sentence2cluster.get(x,None))
        self.documents_df = self.documents_df[pd.notnull(self.documents_df["cluster_id"])][["id", "cluster_id"]]
        self.documents_df = self.documents_df.groupby("id", as_index=False).agg({"cluster_id": lambda x: x.tolist()}).rename(columns={"cluster_id": "clusters"})
        documents_to_save = [DocumentTable(id=row["id"], clusters=row["clusters"]) for idx,row in self.documents_df.iterrows()]

        await ClusterTable.bulk_create(objects=clusters_to_save)
        await DocumentTable.bulk_update(objects=documents_to_save, fields=["clusters"])

    async def run_clustering(self):
        await db_init()
        self.load_model()
        await self.fetch_activity_from_db()
        await self.fetch_activity_documents()
        self.generate_embeddings()
        self.build_clusters()
        self.logger.info(self.clusters)
        await self.save_clusters()
