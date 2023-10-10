<script setup>
import { mapStores } from 'pinia'
import { AdjustmentsHorizontalIcon, MinusCircleIcon } from '@heroicons/vue/24/outline'

import httpClient from '../api/httpClient';
import { FieldType, ellipse } from '../utils/utils'
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
  emits: ['request_search_results', 'reset_search_box'],
  data() {
    return {
      internal_schema_id: null,

      show_negative_query_field: false,
      show_settings: false,
      available_databases: [],
      database_information: {},

      show_search_settings: true,
      show_autocut_settings: false,
      show_vectorize_settings: false,
      show_projection_settings: false,
      show_rendering_settings: false,
      show_other_settings: false,

      available_autocut_strategies: [
        {id: "static_threshold", title: "Static Threshold"},
        {id: "knee_point", title: "Knee Point"},
        {id: "nearest_neighbour_distance_ration", title: "Neighbour Distance"},
      ],
      available_tokenizer: [
        {id: "default", title: "default"},
        {id: "absclust", title: "AbsClust Tokenizer"},
        {id: "simple", title: "simple"},
      ],
      available_dim_reducers: [
        {id: "umap", title: "UMAP"},
        {id: "t_sne", title: "T-SNE"},
        {id: "pca", title: "PCA"},
      ],
      dim_reducer_parameters: {
        "shape": {title: "shape", default: "2d", value: "2d", options: [
          {id: "2d", title: "2D"},
          {id: "1d_plus_distance_polar", title: "1D + Distance (Polar)"},
          {id: "score_graph", title: "Score Graph"},
        ]},
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
    this.internal_schema_id = this.appStateStore.settings.schema_id
    httpClient.post("/organization_backend/available_schemas", {organization_id: -1})
      .then(function (response) {
        that.available_databases = response.data
        that.database_information = {}
        for (const database of that.available_databases) {
          that.database_information[database.id] = database.short_description
        }
        // initial schema_id is set in evaluate_url_query_parameters() in SearchAndMap
      })
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  watch: {
    "appStateStore.settings.schema_id": function (newValue, oldValue) {
      // using internal variable to be able to reset parameters before
      // actually changing global schema_id in select-field listener below
      this.internal_schema_id = this.appStateStore.settings.schema_id
    },
    "appStateStore.schema": function (newValue, oldValue) {
      this.on_full_schema_object_loaded()
    },
    show_negative_query_field() {
      if (!this.show_negative_query_field) {
        this.appStateStore.settings.search.all_field_query_negative = ""
      }
    }
  },
  methods: {
    schema_id_changed_by_user() {
      const clean_settings = JSON.parse(JSON.stringify(this.appStateStore.default_settings))
      clean_settings.schema_id = this.internal_schema_id
      this.appStateStore.settings = clean_settings

      const emptyQueryParams = new URLSearchParams();
      emptyQueryParams.set("schema_id", this.appStateStore.settings.schema_id);
      history.pushState(null, null, "?" + emptyQueryParams.toString());
    },
    on_full_schema_object_loaded() {
      if (this.appStateStore.schema === null) return;
      if (!this.appStateStore.schema.object_fields) return

      const that = this

      // initialize available search fields:
      this.appStateStore.settings.search.separate_queries = {}
      for (const field of Object.values(this.appStateStore.schema.object_fields)) {
        if (field.is_available_for_search) {
          this.appStateStore.settings.search.separate_queries[field.identifier] = {
            query: "",
            query_negative: "",
            must: false,
            threshold_offset: 0.0,
            use_for_combined_search: that.appStateStore.schema.default_search_fields.includes(field.identifier),
          }
        }
      }

      // initialize available number and vector fields:
      that.appStateStore.settings.vectorize.map_vector_field = null
      that.appStateStore.available_vector_fields = []
      that.appStateStore.available_number_fields = []
      for (const field_identifier in that.appStateStore.schema.object_fields) {
        const field = that.appStateStore.schema.object_fields[field_identifier]
        if (field.field_type == FieldType.VECTOR) {
          that.appStateStore.available_vector_fields.push(field.identifier)
          if (field.is_available_for_search && this.appStateStore.schema.default_search_fields.includes(field.identifier)) {
            that.appStateStore.settings.vectorize.map_vector_field = field.identifier
          }
        } else if (field.field_type == FieldType.INTEGER || field.field_type == FieldType.FLOAT) {
          that.appStateStore.available_number_fields.push(field.identifier)
        }
      }
      that.appStateStore.settings.rendering.point_size = 'equal'
      if (that.appStateStore.available_number_fields.length > 0) {
        for (const field of that.appStateStore.available_number_fields) {
          if (field === 'citedby') {
            // prefer this field even if it is not the first one:
            that.appStateStore.settings.rendering.point_size = field
            break
          }
        }
        if (that.appStateStore.settings.rendering.point_size == 'equal')  {
          that.appStateStore.settings.rendering.point_size = that.appStateStore.available_number_fields[0]
        }
      }
    },
  }
}

</script>

<template>
  <div>
    <!-- Database Selection -->
    <div class="flex justify-between">
      <select v-model="internal_schema_id" @change="schema_id_changed_by_user" class="pl-2 pr-8 pt-1 pb-1 mb-2 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
        <option v-for="item in available_databases" :value="item.id" selected>{{ item.name_plural }}</option>
      </select>
      <span class="pl-2 pr-2 pt-1 pb-1 mb-2 text-gray-500 text-sm text-right">{{ database_information[appState.settings.schema_id] }}</span>
    </div>

    <!-- Search Field -->
    <div class="flex">
      <!-- note: search event is not standard -->
      <div class="flex-1 h-9 flex flex-row items-center">
        <input v-if="appState.settings.search.search_type == 'external_input'" type="search" name="search" @search="$emit('request_search_results')" v-model="appState.settings.search.all_field_query"
        placeholder="Search"
        class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 ring-1
      ring-inset ring-gray-300 placeholder:text-gray-400
      focus:ring-2 focus:ring-inset focus:ring-blue-400
      sm:text-sm sm:leading-6 shadow-sm" />
        <button v-if="appState.settings.search.search_type == 'cluster'"
          @click="$emit('reset_search_box')"
          class="flex-none rounded-xl bg-blue-400 px-3 text-white">
          Cluster '{{ ellipse(appState.settings.search.origin_display_name, 15) }}', X
        </button>
        <button v-if="appState.settings.search.search_type == 'similar_to_item'"
          @click="$emit('reset_search_box')"
          class="flex-none rounded-xl bg-blue-400 px-3 text-white">
          Similar to item '{{ ellipse(appState.settings.search.origin_display_name, 15) }}', X
        </button>
        <button v-if="appState.settings.search.search_type == 'collection'"
          @click="$emit('reset_search_box')"
          class="flex-none rounded-xl bg-blue-400 px-3 text-white">
          Collection '{{ ellipse(appState.settings.search.origin_display_name, 15) }}', X
        </button>
        <button v-if="appState.settings.search.search_type == 'recommended_for_collection'"
          @click="$emit('reset_search_box')"
          class="flex-none rounded-xl bg-blue-400 px-3 text-white">
          Recommended for Collection '{{ ellipse(appState.settings.search.origin_display_name, 15) }}', X
        </button>
      </div>
      <button title="Negative Search" @click="show_negative_query_field = !show_negative_query_field" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': show_negative_query_field, 'text-gray-500': !show_negative_query_field }">
        <MinusCircleIcon></MinusCircleIcon>
      </button>
      <button @click="show_settings = !show_settings" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': show_settings, 'text-gray-500': !show_settings }">
        <AdjustmentsHorizontalIcon></AdjustmentsHorizontalIcon>
      </button>
    </div>
    <div v-if="show_negative_query_field || appState.settings.search.all_field_query_negative" class="mt-2 h-9">
      <input v-if="appState.settings.search.search_type == 'external_input'" type="search" name="negative_search" @search="$emit('request_search_results')" v-model="appState.settings.search.all_field_query_negative"
          placeholder="Negative Search"
          class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 ring-1
          ring-inset ring-gray-300 bg-red-100/50 placeholder:text-gray-400
          focus:ring-2 focus:ring-inset focus:ring-blue-400
          sm:text-sm sm:leading-6 shadow-sm" />
    </div>

    <!-- Parameters Area -->
    <div v-show="show_settings" class="mt-3">
      <div button @click="show_search_settings = !show_search_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Search {{ show_search_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_search_settings">
        <div v-if="!appState.settings.search.use_separate_queries" v-for="field in Object.keys(appState.settings.search.separate_queries)" class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">{{ field }}:</span>
          <input v-model="appState.settings.search.separate_queries[field].use_for_combined_search" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Use separate queries:</span>
          <input v-model="appState.settings.search.use_separate_queries" type="checkbox">
        </div>
        <div v-if="appState.settings.search.use_separate_queries" v-for="field in Object.keys(appState.settings.search.separate_queries)" class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">{{ field }}:</span>
          <input v-model.number="appState.settings.search.separate_queries[field].query" placeholder="positive" class="w-1/2 text-gray-500 text-sm">
          <input v-model.number="appState.settings.search.separate_queries[field].query_negative" placeholder="negative" class="w-1/2 text-gray-500 text-sm">
          Must:<input v-model="appState.settings.search.separate_queries[field].must" type="checkbox">
          T.O.<input v-model.number="appState.settings.search.separate_queries[field].threshold_offset" type="range" min="-1.0" max="1.0" step="0.1" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Exclude items below thresholds:</span>
          <input v-model="appState.settings.search.use_similarity_thresholds" type="checkbox">
        </div>
      </div>
      <div button @click="show_autocut_settings = !show_autocut_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Autocut {{ show_autocut_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_autocut_settings">
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Use Autocut:</span>
          <input v-model="appState.settings.search.use_autocut" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Debug Autocut:</span>
          <input v-model="appState.debug_autocut" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Autocut Strategy:</span>
          <select v-model="appState.settings.search.autocut_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option v-for="item in available_autocut_strategies" :value="item.id" selected>{{ item.title }}</option>
          </select>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Autocut min. results:</span>
          <input v-model.number="appState.settings.search.autocut_min_results" class="w-1/2 text-gray-500 text-sm">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Autocut min. score:</span>
          <input v-model.number="appState.settings.search.autocut_min_score" class="w-1/2 text-gray-500 text-sm">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Autocut max. gradient:</span>
          <input v-model.number="appState.settings.search.autocut_max_relative_decline" class="w-1/2 text-gray-500 text-sm">
        </div>
      </div>
      <div button @click="show_vectorize_settings = !show_vectorize_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Vectorization {{ show_vectorize_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_vectorize_settings">
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Max. items for map:</span>
          <span class="text-gray-500 text-sm"> {{ appState.settings.search.max_items_used_for_mapping }} </span>
          <input v-model.number="appState.settings.search.max_items_used_for_mapping" type="range" min="10" max="10000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Create projection using:</span>
          <select v-model="appState.settings.vectorize.map_vector_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
            <option value="w2v_vector" selected>Context-trained W2V Model</option>
            <option v-for="item in appState.available_vector_fields" :value="item" selected>{{ item }}</option>
          </select>
        </div>
      </div>
      <div button @click="show_projection_settings = !show_projection_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Projection {{ show_projection_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_projection_settings">
        <!-- <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Tokenizer:</span>
          <select v-model="appState.settings.vectorize.tokenizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
              <option v-for="item in available_tokenizer" :value="item.id" selected>{{ item.title }}</option>
          </select>
        </div> -->
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Dim. Red. Shape:</span>
          <select v-model="appState.settings.projection.shape" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
              <option v-for="item in dim_reducer_parameters.shape.options" :value="item.id" selected>{{ item.title }}</option>
          </select>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">UMAP n_neighbors:</span>
          <span class="text-gray-500 text-sm"> {{ appState.settings.projection.n_neighbors }} </span>
          <input v-model.number="appState.settings.projection.n_neighbors" type="range" min="1" max="100" step="1" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">UMAP min_dist:</span>
          <span class="text-gray-500 text-sm"> {{ appState.settings.projection.min_dist }} </span>
          <input v-model.number="appState.settings.projection.min_dist" type="range" min="0.001" max="0.2" step="0.001" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">UMAP n_epochs:</span>
          <span class="text-gray-500 text-sm"> {{ appState.settings.projection.n_epochs }} </span>
          <input v-model.number="appState.settings.projection.n_epochs" type="range" min="10" max="3000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">UMAP metric:</span>
          <input v-model.number="appState.settings.projection.metric" class="w-1/2 text-gray-500 text-sm">
        </div>
      </div>
      <div button @click="show_rendering_settings = !show_rendering_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Clustering & Rendering {{ show_rendering_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_rendering_settings">
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Cluster min. samples:</span>
          <input v-model.number="appState.settings.rendering.clusterizer_parameters.min_samples" class="w-1/2 text-gray-500 text-sm">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Cluster min. size: (auto: -1)</span>
          <input v-model.number="appState.settings.rendering.clusterizer_parameters.min_cluster_size" class="w-1/2 text-gray-500 text-sm">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Cluster 'leaf' mode (smaller clusters):</span>
          <input v-model="appState.settings.rendering.clusterizer_parameters.leaf_mode" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Point Size:</span>
          <select v-model="appState.settings.rendering.point_size" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
              <option :value="'equal'" selected>---</option>
              <option v-for="item in appState.available_number_fields" :value="item">{{ item }}</option>
          </select>
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Point Color:</span>
          <select v-model="appState.settings.rendering.point_color" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
              <option :value="'cluster'" selected>Cluster</option>
          </select>
        </div>
      </div>
      <div button @click="show_other_settings = !show_other_settings" class="flex flex-row items-center hover:bg-blue-100">
        <hr class="flex-1"> <span class="flex-none mx-2 text-sm text-gray-500">Other {{ show_other_settings ? 'v' : '>' }}</span> <hr class="flex-1">
      </div>
      <div v-show="show_other_settings">
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Ignore cache:</span>
          <input v-model="appState.ignore_cache" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Store search history:</span>
          <input v-model="appState.store_search_history" type="checkbox">
        </div>
        <div class="flex justify-between items-center">
          <span class="text-gray-500 text-sm">Show timings:</span>
          <input v-model="appState.show_timings" type="checkbox">
        </div>
      </div>
    </div>
  </div>
</template>
