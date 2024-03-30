import concurrent.futures
import logging
from typing import BinaryIO, Dict, Union

from .utils import split_every


class BasePDFParser:
    def fit_transform(self, X: Dict[str, Union[str, bytes, BinaryIO]]):
        failed_ids = []
        parsed = {}
        for batch_keys in split_every(X, self.batch_size):
            batch = {k: X[k] for k in batch_keys}
            p, failed = self._process_batch(batch)
            parsed.update(p)
            failed_ids.extend(failed)
        return parsed, failed_ids

    def _process_batch(self, pdfs: Dict[str, Union[str, bytes, BinaryIO]]):
        parsed_batch = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.n_proc) as executor:
            results = []
            for _id, pdf in pdfs.items():
                r = executor.submit(self._parse_fcn, pdf)
                r._id = _id
                results.append(r)

        failed_ids = []
        for r in concurrent.futures.as_completed(results):
            if r.exception():
                logging.warning(f"{r._id} failed: {repr(r.exception())}")
                failed_ids.append({"filename": r._id, "reason": str(r.exception())})
                continue
            parsed = r.result()
            parsed_batch[r._id] = parsed

        return parsed_batch, failed_ids

    def _parse_fcn(self, pdf):
        raise NotImplementedError