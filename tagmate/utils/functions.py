from io import StringIO
import pandas as pd
import contextlib
import os
import shutil
import stat
import tempfile
from typing import Generator


def bytes_to_df(bytes_data: bytes):
    s = str(bytes_data, "utf-8")
    data = StringIO(s)
    df = pd.read_csv(data).reset_index()
    return df


@contextlib.contextmanager
def SoftTemporaryDirectory(
    suffix: str | None = None,
    prefix: str | None = None,
    dir: str = None,
    **kwargs,
) -> Generator[str, None, None]:
    """
    Context manager to create a temporary directory and safely delete it.
    """

    tmpdir = tempfile.TemporaryDirectory(
        prefix=prefix, suffix=suffix, dir=dir, **kwargs
    )
    yield tmpdir.name

    def _set_write_permission_and_retry(func, path, excinfo):
        os.chmod(path, stat.S_IWRITE)
        func(path)

    try:
        # First once with normal cleanup
        shutil.rmtree(tmpdir.name)
    except Exception:
        # If failed, try to set write permission and retry
        try:
            shutil.rmtree(tmpdir.name, onerror=_set_write_permission_and_retry)
        except Exception:
            pass

    # And finally, cleanup the tmpdir.
    # If it fails again, give up but do not throw error
    try:
        tmpdir.cleanup()
    except Exception:
        pass
