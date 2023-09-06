<script setup>

import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()

</script>

<script>

export default {
  data() {
    return {
      available_search_strategies: [
        {id: "typesense", title: "Keyword-based (Typesense)", parameters: []},
        {id: "vector", title: "Vector Similarity", parameters: []},
        {id: "hybrid", title: "Hybrid (Vector + BM25)",
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

      // UI only:
      show_timings: false,
    }
  },
  mounted() {
  },
}

</script>

<template>
  <div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Search Vector Field:</span>
      <select v-model="appState.settings.search_settings.search_vector_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in appState.available_vector_fields" :value="item" selected>{{ item }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Map Vector Field:</span>
      <select v-model="appState.settings.vectorize_settings.map_vector_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in appState.available_vector_fields" :value="item" selected>{{ item }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Search Strategy:</span>
      <select v-model="appState.settings.search_settings.search_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_search_strategies" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Tokenizer:</span>
      <select v-model="appState.settings.vectorize_settings.tokenizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_tokenizer" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Vectorizer:</span>
      <select v-model="appState.settings.vectorize_settings.vectorizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_vectorizers" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Cluster Title Strategy:</span>
      <select v-model="appState.settings.render_settings.clusterizer_parameters.cluster_title_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_cluster_title_strategies" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
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
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Max. items for map:</span>
      <span class="text-gray-500 text-sm"> {{ appState.settings.search_settings.max_items_used_for_mapping }} </span>
      <input v-model.number="appState.settings.search_settings.max_items_used_for_mapping" type="range" min="10" max="10000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Point Size:</span>
      <select v-model="appState.settings.render_settings.point_size_field" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option :value="null" selected>---</option>
          <option v-for="item in appState.available_number_fields" :value="item">{{ item }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Show timings:</span>
      <input v-model="show_timings" type="checkbox">
    </div>
  </div>
</template>
