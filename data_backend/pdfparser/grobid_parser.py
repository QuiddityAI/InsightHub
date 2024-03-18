import scipdf

from .base_parser import BasePDFParser


class GROBIDParser(BasePDFParser):
    def __init__(
        self,
        grobid_address="http://localhost:8070",
        batch_size=64,
        n_proc=8,
        fulltext=True,
        as_list=False,
        return_coordinates=False,
        parse_figures=False,
    ) -> None:
        super().__init__()

        self.grobid_address = grobid_address
        self.batch_size = batch_size
        self.n_proc = n_proc
        self.fulltext = (fulltext,)
        self.as_list = (as_list,)
        self.return_coordinates = (return_coordinates,)
        self.parse_figures = parse_figures

    def _parse_fcn(self, pdf):
        if not isinstance(pdf, (str, bytes)):
            pdf = pdf.read()
        return scipdf.parse_pdf_to_dict(
            pdf,
            fulltext=self.fulltext,
            soup=True,
            as_list=self.as_list,
            return_coordinates=self.return_coordinates,
            grobid_url=self.grobid_address,
            #parse_figures=self.parse_figures,
        )