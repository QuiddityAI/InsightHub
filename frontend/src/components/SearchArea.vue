<script setup>
import { mapStores } from 'pinia'
import { AdjustmentsHorizontalIcon } from '@heroicons/vue/24/outline'

import httpClient from '../api/httpClient';
import { FieldType } from '../utils/utils'
import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()

</script>

<script>

// combined: all fields in "default search fields" with same query (+negatives), as OR, reciprocal rank fusion

// fulltext: opensearch, all text fields, opensearch dql language for negatives
//    - "must": add to AND set
// description_vector: vector search, knee threshold function, minus operator for negatives
//    - generator -> embedding space -> other generators -> set of types -> fields
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// image_vector: vector search, knee threshold function, minus operator for negatives
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// filter out items that are not in AND sets, reciprocal rank fusion

// auto generated filter criteria set (later, maybe simple ones for now)

// external input: combined (pos, neg, text),
//     separate fields (pos, neg with text or image (if supported)),
// similar to item (list of fields, e.g. descr. or image, fields are OR),
// matching to collection (collection id),
// cluster id of map id


export default {
  props: ["schema"],
  data() {
    return {
      show_settings: false,
      available_databases: [],
      database_information: {},

      separate_search_fields: [],

      available_search_strategies: [
        {id: "fulltext", title: "Keyword-Based", parameters: []},
        {id: "vector", title: "Vector Similarity", parameters: []},
        {id: "hybrid", title: "Hybrid (Vector + Keyword)",
          parameters: [{id: "merging_strategy", options: ["alternating", "rank_fusion"], default: "rank_fusion"}]},
      ],
      available_tokenizer: [
        {id: "default", title: "default"},
        {id: "absclust", title: "AbsClust Tokenizer"},
        {id: "simple", title: "simple"},
      ],
      available_vectorizers: [
        {id: "pubmedbert", title: "PubMedBERT"},
        {id: "gensim_w2v_tf_idf", title: "AbsClust Vectorizer"},
        {id: "openai", title: "OpenAI"},
        {id: "tf_idf", title: "Tf-Idf"},
      ],
      available_dim_reducers: [
        {id: "umap", title: "UMAP"},
        {id: "t_sne", title: "T-SNE"},
        {id: "pca", title: "PCA"},
      ],
      dim_reducer_parameters: {
        "shape": {title: "shape", default: "2d", value: "2d", options: [{id: "2d", title: "2D"}, {id: "1d_plus_distance_polar", title: "1D + Distance (Polar)"}]},
        "n_neighbors": {title: "n_neighbors", default: 15, value: 15},
        "min_dist": {title: "min_dist", default: 0.05, value: 0.05},
        "n_epochs": {title: "n_epochs", default: 500, value: 500},
        "metric": {title: "metric", default: "euclidean", value: "euclidean"},
      },
      available_clusterizer: [
        {id: "hdbscan", title: "HDBSCAN"},
      ],
      clusterizer_parameters: {
        "min_cluster_size": {title: "min_cluster_size", default: "auto", value: "auto"},
        "min_samples": {title: "min_samples", default: 5, value: 5},
      },
      available_cluster_title_strategies: [
        {id: "tf_idf_top_3", title: "tf_idf_top_3"},
        {id: "generative_ai", title: "generative_ai"},
      ],
    }
  },
  mounted() {
    const that = this
    httpClient.post("/organization_backend/available_schemas", {organization_id: -1})
      .then(function (response) {
        that.available_databases = response.data
        that.database_information = {}
        for (const database of that.available_databases) {
          that.database_information[database.id] = database.short_description
        }
        that.appStateStore.settings.schema_id = 1
      })
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  watch: {
    schema: function (newValue, oldValue) {
      const that = this
      const separate_search_fields = []
      this.appStateStore.settings.search_settings.separate_queries = {}
      for (const field of Object.values(this.schema.object_fields)) {
        if (field.is_available_for_search) {
          separate_search_fields.push(field)
          this.appStateStore.settings.search_settings.separate_queries[field.identifier] = {
            query: "",
            query_negative: "",
            must: false,
            threshold_offset: 0.0,
          }
        }
      }
      this.separate_search_fields = separate_search_fields

      that.appStateStore.available_vector_fields = []
      that.appStateStore.available_number_fields = []
      for (const field_identifier in that.schema.object_fields) {
        const field = that.schema.object_fields[field_identifier]
        //if (field.is_available_for_search && field.field_type == FieldType.VECTOR) {
        if (field.field_type == FieldType.VECTOR) {
          that.appStateStore.available_vector_fields.push(field.identifier)
        } else if (field.field_type == FieldType.INTEGER || field.field_type == FieldType.FLOAT) {
          that.appStateStore.available_number_fields.push(field.identifier)
        }
        if (that.appStateStore.available_vector_fields.length > 0) {
          that.appStateStore.settings.search_settings.search_vector_field = that.appStateStore.available_vector_fields[0]
          that.appStateStore.settings.vectorize_settings.map_vector_field = that.appStateStore.available_vector_fields[0]
        } else {
          that.appStateStore.settings.search_settings.search_vector_field = null
          that.appStateStore.settings.vectorize_settings.map_vector_field = null
        }
        if (that.appStateStore.available_number_fields.length > 0) {
          that.appStateStore.settings.render_settings.point_size_field = that.appStateStore.available_number_fields[0]
        } else {
          that.appStateStore.settings.search_settings.point_size_field = null
        }
      }
    },
  },
}

</script>

<template>
  <div>
    <!-- Database Selection -->
    <div class="flex justify-between">
      <select v-model="appState.settings.schema_id" class="pl-2 pr-8 pt-1 pb-1 mb-2 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
        <option v-for="item in available_databases" :value="item.id" selected>{{ item.name_plural }}</option>
      </select>
      <span class="pl-2 pr-2 pt-1 pb-1 mb-2 text-gray-500 text-sm text-right">{{ database_information[appState.settings.schema_id] }}</span>
    </div>

    <!-- Search Field -->
    <div class="flex">
      <!-- note: search event is not standard -->
      <input type="search" name="search" @search="request_search_results" v-model="appState.settings.search_settings.all_field_query"
        placeholder="Search"
        class="w-full rounded-md border-0 py-1.5 text-gray-900 ring-1
      ring-inset ring-gray-300 placeholder:text-gray-400
      focus:ring-2 focus:ring-inset focus:ring-blue-400
      sm:text-sm sm:leading-6 shadow-sm" />
      <button @click="show_settings = !show_settings" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': show_settings, 'text-gray-500': !show_settings }">
        <AdjustmentsHorizontalIcon></AdjustmentsHorizontalIcon>
      </button>
    </div>

    <!-- Parameters Area -->
    <div v-show="show_settings" class="mt-3">
      <div v-if="!appState.settings.search_settings.use_separate_queries" class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Search Strategy:</span>
        <select v-model="appState.settings.search_settings.combined_search_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in available_search_strategies" :value="item.id" selected>{{ item.title }}</option>
        </select>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Use separate queries:</span>
        <input v-model="appState.settings.search_settings.use_separate_queries" type="checkbox">
      </div>
      <div v-if="appState.settings.search_settings.use_separate_queries" v-for="field in separate_search_fields" class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">{{ field.identifier }}:</span>
        <input v-model.number="appState.settings.search_settings.separate_queries[field.identifier].query" placeholder="positive" class="w-1/2 text-gray-500 text-sm">
        <input v-model.number="appState.settings.search_settings.separate_queries[field.identifier].query_negative" placeholder="negative" class="w-1/2 text-gray-500 text-sm">
        Must:<input v-model="appState.settings.search_settings.separate_queries[field.identifier].must" type="checkbox">
        T.O.<input v-model.number="appState.settings.search_settings.separate_queries[field.identifier].threshold_offset" type="range" min="-1.0" max="1.0" step="0.1" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
      </div>
      <!-- <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Search Vector Field:</span>
        <select v-model="appState.settings.search_settings.search_vector_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in appState.available_vector_fields" :value="item" selected>{{ item }}</option>
        </select>
      </div> -->
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Max. items for map:</span>
        <span class="text-gray-500 text-sm"> {{ appState.settings.search_settings.max_items_used_for_mapping }} </span>
        <input v-model.number="appState.settings.search_settings.max_items_used_for_mapping" type="range" min="10" max="10000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
      </div>
      <hr>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Use context-trained w2v model:</span>
        <input v-model="appState.settings.vectorize_settings.use_w2v_model" type="checkbox">
      </div>
      <div v-if="!appState.settings.vectorize_settings.use_w2v_model" class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Map Vector Field:</span>
        <select v-model="appState.settings.vectorize_settings.map_vector_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in appState.available_vector_fields" :value="item" selected>{{ item }}</option>
        </select>
      </div>
      <hr>
      <!-- <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Tokenizer:</span>
        <select v-model="appState.settings.vectorize_settings.tokenizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in available_tokenizer" :value="item.id" selected>{{ item.title }}</option>
        </select>
      </div> -->
      <!-- <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Vectorizer:</span>
        <select v-model="appState.settings.vectorize_settings.vectorizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in available_vectorizers" :value="item.id" selected>{{ item.title }}</option>
        </select>
      </div> -->
      <!-- <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Cluster Title Strategy:</span>
        <select v-model="appState.settings.render_settings.clusterizer_parameters.cluster_title_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in available_cluster_title_strategies" :value="item.id" selected>{{ item.title }}</option>
        </select>
      </div> -->
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Dim. Red. Shape:</span>
        <select v-model="appState.settings.projection_settings.shape" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in dim_reducer_parameters.shape.options" :value="item.id" selected>{{ item.title }}</option>
        </select>
      </div>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">UMAP n_neighbors:</span>
        <span class="text-gray-500 text-sm"> {{ appState.settings.projection_settings.n_neighbors }} </span>
        <input v-model.number="appState.settings.projection_settings.n_neighbors" type="range" min="1" max="100" step="1" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
      </div>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">UMAP min_dist:</span>
        <span class="text-gray-500 text-sm"> {{ appState.settings.projection_settings.min_dist }} </span>
        <input v-model.number="appState.settings.projection_settings.min_dist" type="range" min="0.001" max="0.2" step="0.001" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
      </div>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">UMAP n_epochs:</span>
        <span class="text-gray-500 text-sm"> {{ appState.settings.projection_settings.n_epochs }} </span>
        <input v-model.number="appState.settings.projection_settings.n_epochs" type="range" min="10" max="3000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
      </div>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">UMAP metric:</span>
        <input v-model.number="appState.settings.projection_settings.metric" class="w-1/2 text-gray-500 text-sm">
      </div>
      <hr>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Point Size:</span>
        <select v-model="appState.settings.render_settings.point_size_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option :value="null" selected>---</option>
            <option v-for="item in appState.available_number_fields" :value="item">{{ item }}</option>
        </select>
      </div>
      <hr>
      <div class="flex justify-between items-center">
        <span class="text-gray-500 text-sm">Show timings:</span>
        <input v-model="appState.show_timings" type="checkbox">
      </div>
    </div>
  </div>
</template>
