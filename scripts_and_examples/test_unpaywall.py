import json
import requests

doi = "10.1002/adfm.201801511"
doi = "10.1038/nature12373"
email = "xxx@xxx.com"

result = requests.get(f"https://api.unpaywall.org/v2/{doi}?email={email}")

print(json.dumps(result.json(), indent=2))

# {
#   "doi": "10.1038/nature12373",
#   "doi_url": "https://doi.org/10.1038/nature12373",
#   "title": "Nanometre-scale thermometry in a living cell",
#   "genre": "journal-article",
#   "is_paratext": false,
#   "published_date": "2013-07-31",
#   "year": 2013,
#   "journal_name": "Nature",
#   "journal_issns": "0028-0836,1476-4687",
#   "journal_issn_l": "0028-0836",
#   "journal_is_oa": false,
#   "journal_is_in_doaj": false,
#   "publisher": "Springer Science and Business Media LLC",
#   "is_oa": true,
#   "oa_status": "green",
#   "has_repository_copy": true,
#   "best_oa_location": {
#     "updated": "2022-12-11T02:03:01.991539",
#     "url": "https://dash.harvard.edu/bitstream/1/12285462/1/Nanometer-Scale%20Thermometry.pdf",
#     "url_for_pdf": "https://dash.harvard.edu/bitstream/1/12285462/1/Nanometer-Scale%20Thermometry.pdf",
#     "url_for_landing_page": "http://nrs.harvard.edu/urn-3:HUL.InstRepos:12285462",
#     "evidence": "oa repository (via OAI-PMH doi match)",
#     "license": "cc-by",
#     "version": "publishedVersion",
#     "host_type": "repository",
#     "is_best": true,
#     "pmh_id": "oai:dash.harvard.edu:1/12285462",
#     "endpoint_id": "8c9d8ba370a84253deb",
#     "repository_institution": "Harvard University - Digital Access to Scholarship at Harvard (DASH)",
#     "oa_date": null
#   },

#   "first_oa_location": {
#     "updated": "2023-08-23T05:42:20.987839",
#     "url": "https://escholarship.org/content/qt5035z3pq/qt5035z3pq.pdf?t=ruk3e3",
#     "url_for_pdf": "https://escholarship.org/content/qt5035z3pq/qt5035z3pq.pdf?t=ruk3e3",
#     "url_for_landing_page": "https://escholarship.org/uc/item/5035z3pq",
#     "evidence": "oa repository (via OAI-PMH title and first author match)",
#     "license": null,
#     "version": "submittedVersion",
#     "host_type": "repository",
#     "is_best": false,
#     "pmh_id": "oai:escholarship.org:ark:/13030/qt5035z3pq",
#     "endpoint_id": "29851292c9b5c740cb6",
#     "repository_institution": "University of California - eScholarship University of California",
#     "oa_date": "2023-05-13"
#   },
#   "oa_locations": [
#     {
#       "updated": "2022-12-11T02:03:01.991539",
#       "url": "https://dash.harvard.edu/bitstream/1/12285462/1/Nanometer-Scale%20Thermometry.pdf",
#       "url_for_pdf": "https://dash.harvard.edu/bitstream/1/12285462/1/Nanometer-Scale%20Thermometry.pdf",
#       "url_for_landing_page": "http://nrs.harvard.edu/urn-3:HUL.InstRepos:12285462",
#       "evidence": "oa repository (via OAI-PMH doi match)",
#       "license": "cc-by",
#       "version": "publishedVersion",
#       "host_type": "repository",
#       "is_best": true,
#       "pmh_id": "oai:dash.harvard.edu:1/12285462",
#       "endpoint_id": "8c9d8ba370a84253deb",
#       "repository_institution": "Harvard University - Digital Access to Scholarship at Harvard (DASH)",
#       "oa_date": null
#     },
#     {
#       "updated": "2022-05-06T09:48:48.799280",
#       "url": "https://europepmc.org/articles/pmc4221854?pdf=render",
#       "url_for_pdf": "https://europepmc.org/articles/pmc4221854?pdf=render",
#       "url_for_landing_page": "https://europepmc.org/articles/pmc4221854",
#       "evidence": "oa repository (via OAI-PMH doi match)",
#       "license": null,
#       "version": "acceptedVersion",
#       "host_type": "repository",
#       "is_best": false,
#       "pmh_id": "oai:europepmc.org:PhTpMqCEcd8uKDS6aBuG",
#       "endpoint_id": "b5e840539009389b1a6",
#       "repository_institution": "PubMed Central - Europe PMC",
#       "oa_date": null
#     },
#     {
#       "updated": "2023-09-22T14:24:33.599360",
#       "url": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4221854",
#       "url_for_pdf": null,
#       "url_for_landing_page": "https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4221854",
#       "evidence": "oa repository (via pmcid lookup)",
#       "license": null,
#       "version": "acceptedVersion",
#       "host_type": "repository",
#       "is_best": false,
#       "pmh_id": null,
#       "endpoint_id": null,
#       "repository_institution": null,
#       "oa_date": null
#     },
#     {
#       "updated": "2017-10-22T03:05:35.844774",
#       "url": "https://arxiv.org/pdf/1304.1068",
#       "url_for_pdf": "https://arxiv.org/pdf/1304.1068",
#       "url_for_landing_page": "https://arxiv.org/abs/1304.1068",
#       "evidence": "oa repository (via OAI-PMH doi match)",
#       "license": null,
#       "version": "submittedVersion",
#       "host_type": "repository",
#       "is_best": false,
#       "pmh_id": "oai:arXiv.org:1304.1068",
#       "endpoint_id": "arXiv.org",
#       "repository_institution": "arXiv.org",
#       "oa_date": null
#     },
#     {
#       "updated": "2023-08-23T05:42:20.987839",
#       "url": "https://escholarship.org/content/qt5035z3pq/qt5035z3pq.pdf?t=ruk3e3",
#       "url_for_pdf": "https://escholarship.org/content/qt5035z3pq/qt5035z3pq.pdf?t=ruk3e3",
#       "url_for_landing_page": "https://escholarship.org/uc/item/5035z3pq",
#       "evidence": "oa repository (via OAI-PMH title and first author match)",
#       "license": null,
#       "version": "submittedVersion",
#       "host_type": "repository",
#       "is_best": false,
#       "pmh_id": "oai:escholarship.org:ark:/13030/qt5035z3pq",
#       "endpoint_id": "29851292c9b5c740cb6",
#       "repository_institution": "University of California - eScholarship University of California",
#       "oa_date": "2023-05-13"
#     }
#   ],
#   "oa_locations_embargoed": [],
#   "updated": "2023-08-13T08:37:12.457860",
#   "data_standard": 2,
#   "z_authors": [
#     {
#       "given": "G.",
#       "family": "Kucsko",
#       "sequence": "first"
#     },
#     {
#       "given": "P. C.",
#       "family": "Maurer",
#       "sequence": "additional"
#     },
#     {
#       "given": "N. Y.",
#       "family": "Yao",
#       "sequence": "additional"
#     },
#     {
#       "given": "M.",
#       "family": "Kubo",
#       "sequence": "additional"
#     },
#     {
#       "given": "H. J.",
#       "family": "Noh",
#       "sequence": "additional"
#     },
#     {
#       "given": "P. K.",
#       "family": "Lo",
#       "sequence": "additional"
#     },
#     {
#       "given": "H.",
#       "family": "Park",
#       "sequence": "additional"
#     },
#     {
#       "given": "M. D.",
#       "family": "Lukin",
#       "sequence": "additional"
#     }
#   ]
# }
