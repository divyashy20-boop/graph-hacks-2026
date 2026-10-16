# Audit data attribution and reuse

## Milestone G: frozen public sources and short clause probe

`g_public_sources_v1.json` contains32 further token-joined FewRel validation
excerpts with upstream PID/head/tail classification notes, hashes and UGI metadata.
Attribution: Xu Han et al., *FewRel: A Large-Scale Supervised Few-Shot Relation
Classification Dataset with State-of-the-Art Evaluation*, EMNLP2018,
[paper](https://aclanthology.org/D18-1514/), [THUNLP dataset](https://github.com/thunlp/FewRel),
[licence declaration](https://thunlp.github.io/1/fewrel1.html). This derivative,
including copyrightable added metadata, is **CC BY-SA4.0**, not CC0/code-only.
Changes: selected rows, token joining, hashes/provenance; no exhaustive entailment
or human-review annotations added. Keep attribution and share-alike terms on reuse.
Original Wikipedia article/author identities are unavailable in these records.

`g_novel_public_clause.json` cites NASA/JPL's *Episode6: Air and Shield*, Nov24,2020,
[transcript](https://www.jpl.nasa.gov/podcasts/on-a-mission-season-1/season-3-planet-earth/episode-6-air-and-shield/).
It retains a short attributed narrator quotation/context for a limited research
probe. JPL/Caltech source rights remain; no blanket CC0/public-domain relicensing
of the transcript, audio, photographs or third-party quotations is claimed.
UGI's source/meaning inspection is not NASA/JPL validation or endorsement.
Reports quoting these sources retain their respective terms.

Bundled packs, g_open_development.json and ordinary synthetic schema-demo cases
are AI-authored CC0 development/specification examples, not independent gold.

## Milestone F: T2D correspondence diagnostic

Source: [WDC T2D Gold Standard](https://webdatacommons.org/webtables/goldstandard.html),
entity correspondence archive `entities_instance.tar.gz`. The publisher describes
these row-to-DBpedia mappings as manually generated and licenses the correspondences
under Apache2.0. Web tables and the DBpedia dump have separate terms and are not
downloaded/redistributed by this probe. Archive remains ignored/local; reports
contain hashed row IDs, derived pair labels and measurements, not source surfaces
or DBpedia URIs. Original archive SHA is pinned in the adapter/report. See
MILESTONE_F_REPORT for attribution, sampling and limits; no publisher endorsement.
Synthetic F pair/cluster fixtures and local demo sources are AI-authored CC0 policy
tests, not annotations by T2D authors or independently human reviewed.

Source material is not automatically covered by the repository code's licence.
Preserve each case's source URL, title, locator, excerpt hash and licence fields.
No source publisher endorses UGI. Labels added here are provisional AI work,
not annotations produced or validated by the cited publishers.

## FewRel material

Twenty Wikipedia-derived validation excerpts in `evaluation/c_evaluation.json`
come from **Xu Han, Hao Zhu, Pengfei Yu, Ziyun Wang, Yuan Yao, Zhiyuan Liu and
Maosong Sun (2018), FewRel: A Large-Scale Supervised Few-Shot Relation
Classification Dataset with State-of-the-Art Evaluation, EMNLP,4803–4809**.
[Paper](https://aclanthology.org/D18-1514/),
[THUNLP repository](https://github.com/thunlp/FewRel),
[dataset licence declaration](https://thunlp.github.io/1/fewrel1.html).
The dataset is distributed under [CC BY-SA4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The upstream validation file SHA256 and sampling/exclusion parameters are in
`c_manifest.json`. Changes: token-joined/whitespace-normalized excerpts,
selection of records, UGI provenance/annotation fields; source-entailment labels
are still unreviewed. Upstream relation-classification labels are not exhaustive
source-supported graph annotations. Original Wikipedia page/author identity is
not available in this queue; the dataset-record URL is not an article URL.

The FewRel-derived portion, and our copyrightable additions to its redistributed
derivative fixture, are supplied under CC BY-SA4.0. Keep this attribution and
licence when redistributing/adapting it; do not relabel it CC0 or as code-only
data. Other independently licensed records in the same JSON collection retain
their own terms; this notice does not relicense third-party material. Reports
that reproduce these excerpts/evidence retain the same source terms.

## Other source excerpts

The public cases identify the following agency-authored body-text sources:
NASA Lewis/Apollo13 investigation history, Webb FAQ, Armstrong biography,
Apollo13 review-board history, NIST CHIPS semiconductor-materials vision,
NASA Webb international partnership and NASA SVS integration description;
FTC's May2024 Exxon/Pioneer release; NPS Grand Canyon geological formations.
Exact URLs/titles are preserved per case in `c_source_recipe.json`,
`c_development.json` and `c_evaluation.json`. Excerpts are whitespace-normalized;
provisional relations/roles and surface spans are UGI additions.

The `US-Government-work` metadata describes selected agency-authored text, not
a blanket licence for every asset on those websites. Third-party text, logos,
photographs, privacy/publicity rights and non-US reuse can have separate rules.
See [USAGov guidance](https://www.usa.gov/government-copyright) and
[NASA media policy](https://www.nasa.gov/nasa-brand-center/images-and-media/).
No agency logo or downloaded PDF is redistributed in this commit. The PDF smoke
report references the NASA biography and records a hash; its downloaded photo/
page and rendered preview remain in ignored local files, not repo assets.

The research abstract excerpt comes from **Eoghan Cunningham and Derek Greene,
Knowledge transfer, knowledge gaps, and knowledge silos in citation networks,
PLOS One20(8):e0329302 (2025)**,
[article and licence](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0329302),
under [CC BY4.0](https://creativecommons.org/licenses/by/4.0/).
Changes: selected normalized abstract sentence, provisional UGI event/role labels
and entity spans. This does not imply the authors endorse the event ontology.

Synthetic safety/demo records are identified separately as CC0-1.0. Do not pool
their provenance or accuracy scores with independently authored public sources.
