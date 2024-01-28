<script setup>
import httpClient from "../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import ClassifierClass from "./ClassifierClass.vue"
import { mapStores } from "pinia"
import { useAppStateStore } from "../stores/settings_store"

const appState = useAppStateStore()
</script>

<script>
export default {
  props: ["classifier"],
  emits: ["delete_classifier", "recommend_items_for_classifier", "show_classifier_as_map"],
  data() {
    return {
      settings_visible: false,
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {},
  methods: {
    remove_item_from_classifier(item_id, is_positive) {
      const that = this
      const body = {
        classifier_id: this.classifier.id,
        item_id: item_id,
        is_positive: is_positive,
      }
      httpClient
        .post("/org/data_map/remove_item_from_classifier", body)
        .then(function (response) {
          // 'classifier' prop is read-only, so get writable reference:
          const classifier_index = that.appStateStore.classifiers.findIndex(
            (col) => col.id === that.classifier.id
          )
          const classifier = that.appStateStore.classifiers[classifier_index]

          if (is_positive) {
            const item_index = classifier.positive_ids.indexOf(item_id)
            classifier.positive_ids.splice(item_index, 1)
          } else {
            const item_index = classifier.negative_ids.indexOf(item_id)
            classifier.negative_ids.splice(item_index, 1)
          }
        })
    },
  },
}
</script>

<!-- TODO: add button to train concept, add threshold settings, add checkbox to mark results in map, add color / symbol select box,
  collaps list etc. -->

<template>
  <li>
    <div class="flex flex-row gap-3">
      <span class="font-medium text-gray-500">{{ classifier.name }}</span>
      <div class="flex-1"></div>
      <button
        @click="$emit('recommend_items_for_classifier', classifier)"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Recommend Similar
      </button>
      <button
        @click="$emit('show_classifier_as_map', classifier)"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Show Map
      </button>
      <button
        @click="settings_visible = !settings_visible"
        class="ml-1 w-8 rounded px-1 hover:bg-gray-100"
        :class="{
          'text-blue-600': settings_visible,
          'text-gray-500': !settings_visible,
        }">
        <EllipsisVerticalIcon></EllipsisVerticalIcon>
      </button>
    </div>
    <div v-if="settings_visible" class="mt-2 flex flex-row gap-3">
      <button
        @click="train_classifier"
        class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Train Classifier
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        X: highlight similar in map
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Color: xxx
      </button>
      <button @click="" class="text-sm font-light text-gray-500 hover:text-blue-500/50">
        Symbol: xxx
      </button>
      <!--
    AI usage:
      offline embeddings (using pre-trained model, for search, recom., similarity, filter)
      online embeddings (using pre-trained model, for clustering, sorting, class., tagging, marking)
      online embedding using context model (for clustering and sorting)
      zero-shot training (search, similarity, tags)
      few shot training (collections)
      clustering (UMAP)

    USP: No deep training, focus on foundation / pre-trained models with search + zero-few-shot classifiers!

    Potential:
      learn classifiers from existing examples
      gen AI for cluster labels
      gen AI for summaries
      RAG gen AI chat
      face detection
      industry specific taxonomies (tags, genres, etc.)
      industry specific sorting (aesthetics, quality, conversion, brand matching, etc.)
      industry specific classification (content moderation)
      -> list of pre-trained models for embeddings, and list of pre-collected classifiers based on those embeddings

    classifier dataset types:
      zero-shot (external short text or image)
      example (item from DB)
      few-shot (collection)
      many-shot (examples from existing tagged database)

    classifier training types:
      direct similarity to example or collection average (pos. minus neg.)
      trained binary classifying vector, one or more pos. and neg. examples (inference with dot-product)
      multi-class classifier (one-hot output, one dot-vector per class, training knows other classes)
      multi-class tagging (multiple possible, one dot-vector per class, training knows other classes)

    -> each classifier is a vector that is applied using dot-product and might have threshold

    each classifier can be used for:
      search (direct kNN using single vector or recommendation search using collection)
      similarity search (technically search, but different use case)
      recommendation (technically search, but different use case)
      filter (if threshold is set)
      sorting (sort search results generated by other classifier or fulltext)
      online / offline classifying (highest score of list of classifiers)
      online / offline tagging (list of cl. above threshold or all sorted by scores)
      marking in map and result list (th. [star symbol, glow] or linear [point size, saturation],
          should be in render settings)

    x add button to make current search settings the default (or store them)

    Search:
    - one classifier per vector field
    - "combined query" is an on-demand classifier creator that is used for all fields smartly
    - "separate queries" are on-demand classifier creators per vector field

    Organization Backend:
    - classifier list per dataset (collections)
    - classifier groups, each classifier can be in multiple groups,
        groups can create multi-class classifiers (using other positives as negative for a class)
    - each classifier has list of pos and neg text / image examples, vectors, or ids (?!)
        -> collections (with checkbox for manually created or not, or in group "manual collections")
    - upload button to upload group of classifiers
        - e.g. from list of pos texts (zero-shot tags)
        - or pos and neg images examples for each (using URL or ID) (learned tags (curated or from existing DB), genres)
    - UI to show pos and neg examples (with score each) per classifier and examples above and below threshold from current dataset
        -> collection view, but extended

    - or more general list of "examples / training items": item (id, text or vector) plus pos and hard neg classes?
        - would facilitate training multi-class classifiers, taggers
        - maybe bad performance to retrieve all examples of specific collection?
        - existing "collections / tags" is implicit, expensive to retrieve

    - how to store external examples (texts, images, documents, websites)?
        - if stored as vector, its not possible to change embedding type later on
        - if stored plain, dataset is unclear
        - if stored in dataset, has to be marked as external or separate table, and need to comply with dataset
        - if stored in dataset, not universal to multiple fields (e.g. t-shirt class can apply to front and back images)

    Binary Classifier / Recommendation / Score using examples:
        - Collection (document type, favorites, moderation, editorial)
        - improve: add wrong item to collection
        - how to add examples not in DB?
    Multi-classifier using examples:
        - class field of item (dropdown /w add) (document type, incident class, fault type, product class)
        - manual and auto class field
        - improve: change manual class of item
        - how to add examples not in DB?
    Multi-tagging using examples:
        - tag list field of item (tag field /w add) (image tags, etc)
        - improve: if tag is missing -> add tag to item
                   if tag is too much: add to manual negative tag list?
        - how to add examples not in DB?

    Classifier Group object:
        - example item dataset
        - Name
        - base classifier link
        - single class / binary? -> field for class name (used if class is empty)
        - if multi: exclusive: yes / no
        - global threshold
        - per class threshold changes
        - always one embedding space -> one classifying vector per class
            - future: combination classifiers, combining classifier results using linear or neural combination?
        - embedding space (for external examples and target field) (OpenCLIP, E5 etc.)
        - vector field for item examples (title+abstract vector, main image vector (allow to apply it to secondary images) etc.)

        - Notes:
          - should allow to change embedding of database without redoing all classifiers
          - reasons to allow storing vectors: how to store feedback from vector with multiple source fields? -> id type
          - review paper: title, abstract E5 (not authors, images), source: examples + text snippets, applicable on any text-based E5 vector
            - improvement: false positive, thumbs down: add to neg collection if col
          - zero shot image tags: tag name CLIP variation, source not in DB, applicable to any image CLIP vector
            - improvement: add item id with pos and hard neg to external examples

          - Collections could be one classifier group?


          - or multiple spaces, multiple classifier vectors, and then score aggregation?
          - but mapping field -> space doesn't work for external example (or each need space, or different lists per space)
          - and mapping type -> space doesn't allow to exclude item fields (url, author etc.)
          - or using default search fields?

        - train now (or dirty field?)
        - existing examples (stored in DB): (fields used to store feedback if set, otherwise in external examples with id)
          - one bool field of item (if binary)
          - one class field of item (if exclusive)
          - one tag field of item (pos) (if multi)
          - one tag field of item (hard negatives) (if multi)
        - external / additional examples: type, content (text / image URL), classes, checkbox hard negatives
          - image tags: IMAGE, image_url, landscape;hill;sky
          - image tags hard negatives (from user feedback): desert;mountain, checkbox hard negatives: y
          - conecept pos: IMAGE, image_url, eiffel_tower, not: -
          - conecept neg: IMAGE, image_url, -, not: eiffel_tower
          - zero shot tag: TEXT, eiffel tower, eiffel_tower, not: -
          - zero shot tag (neg): TEXT, cell tower, -, not: eiffel_tower
          - content moderation: IMAGE, image_url, eiffel_tower, not: - (see concept)
          - review paper: TEXT, review of different studies..., review_paper, not: -
          - review paper: TEXT, our experiments show that..., -, not: review_paper

product type: chrous dataset, title_field has title, product type in type_
 -> "chorus product type base classifier"
then customer product dataset: title field, used for feedback, using custom fine tuned FashionCLIP

relevant fields in this dataset: leave blank to use default search fields (or sources of default search vectors)
  -> if fields and target embedding space match a vector field -> use that

models / decision vectors: { embedding_space / model_type (fasttext): vector / model, class: xxx, last updated: xxx }
-> can be updated for each class individually

paper type from small dataset
then using it for title / title+abstract using E5, PubMedBERT etc.

A on demand: after doing search, apply on results, show thumbs up / down per class -> add to examples
    problems: not persisted, done for every search
B fill missing values of field using classifer: up down -> write to field, but done on demand
C extra field for classifier results: done offline, but needs to be updated, feedback can be written to annotation field if present
D Collections always stored as examples, feedback adds or removes from examples



    Classifiers vs Fields:
    - fields contain:
        - external data (descr., image, ids, price, citations)
        - data that takes long to calculate (embeddings, summaries, gen AI)
        - calculations that only depend on other item fields (descr.) and pre-trained models
          -> not collection classifiers as they change when collection changes
    - computed fields (not stored in DB but specified in dataset):
        - actually applicable / often used classifiers (aesthetic score, image tags)
          -> anything that should show up by default in UI and should be exported
        - aggregations -> on-demand / changing fields that need configuration (source fields)
    - rest of classifiers / on-demand calculations:
        - available in dropdown to select (industry-specific tags lists, generic classifiers, collections)

    Questions:
    - how to handle large number of zero shot or trained classifiers (list of tag names, or database with examples)
    - how to add zero shot classifiers: in a separate list or on-demand where needed?
        - but difficult with images
        - where to set threshold and help to set it
    - how to do offline tagging / classifying
    - how to do exhaustive search using collection -> classifying all items in DB
    - how to integrate "separate search queries" into this structure
    - how to handle multiple classifiers per search, filter, recommend, mark etc.

    -->

      <!-- for review, dataset: global classifier: X -->
      <!-- for high conversion image: use score for point size: X -->
      <!-- for pride tag: add to global filter list: X -->
      <!-- for high aesthetic: sort result list with this: X -->
      <!-- for landscape tag: somewhere else: apply this classifier to all items (where to store?) -->
      <div class="flex-1"></div>
      <button
        @click="$emit('delete_classifier', classifier.id)"
        class="ml-1 w-6 rounded px-1 text-gray-500 hover:bg-red-100">
        <TrashIcon></TrashIcon>
      </button>
    </div>
    <ClassifierClass
      v-for="class_name in classifier.actual_classes"
      :key="class_name"
      :classifier="classifier"
      :class_name="class_name">
    </ClassifierClass>
  </li>
</template>

<style scoped></style>
