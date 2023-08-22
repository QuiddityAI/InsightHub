<script setup>
</script>

<script>

export default {
  data() {
    return {

      // settings:
      available_search_strategies: [
        {id: "typesense", title: "Keyword-based (Typesense)", parameters: []},
        {id: "vector", title: "Vector Similarity", parameters: []},
        {id: "hybrid", title: "Hybrid (Vector + BM25)",
          parameters: [{id: "merging_strategy", options: ["alternating", "rank_fusion"], default: "rank_fusion"}]},
      ],
      selected_search_strategy: "typesense",
      result_list_items_per_page: 10,
      result_list_current_page: 0,
      result_list_max_pages: 20,  // needed?
      max_items_used_for_mapping: 2000,
      available_tokenizer: [
        {id: "default", title: "default"},
        {id: "absclust", title: "AbsClust Tokenizer"},
        {id: "simple", title: "simple"},
      ],
      selected_tokenizer: "default",
      available_vectorizers: [
        {id: "pubmedbert", title: "PubMedBERT"},
        {id: "gensim_w2v_tf_idf", title: "AbsClust Vectorizer"},
        {id: "openai", title: "OpenAI"},
        {id: "tf_idf", title: "Tf-Idf"},
      ],
      selected_vectorizer: "pubmedbert",
      available_dim_reducers: [
        {id: "umap", title: "UMAP"},
        {id: "t_sne", title: "T-SNE"},
        {id: "pca", title: "PCA"},
      ],
      selected_dim_reducer: "umap",
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
      selected_clusterizer: "hdbscan",
      clusterizer_parameters: {
        "min_cluster_size": {title: "min_cluster_size", default: "auto", value: "auto"},
        "min_samples": {title: "min_samples", default: 5, value: 5},
      },
      available_cluster_title_strategies: [
        {id: "tf_idf_top_3", title: "tf_idf_top_3"},
        {id: "generative_ai", title: "generative_ai"},
      ],
      selected_cluster_title_strategy: "tf_idf_top_3",

      // UI only:
      show_timings: false,
    }
  },
  methods: {
    get_parameters() {
      return {
        search_strategy: this.selected_search_strategy,
        tokenizer: this.selected_tokenizer,
        vectorizer: this.selected_vectorizer,
        cluster_title_strategy: this.selected_cluster_title_strategy,
        dim_reducer_parameters: {
          shape: this.dim_reducer_parameters.shape.value,
          n_neighbors: this.dim_reducer_parameters.n_neighbors.value,
          min_dist: this.dim_reducer_parameters.min_dist.value,
          n_epochs: this.dim_reducer_parameters.n_epochs.value,
          metric: this.dim_reducer_parameters.metric.value,
        },
        max_items_used_for_mapping: this.max_items_used_for_mapping,
      }
    }
  },
  mounted() {
  },
}

</script>

<template>
  <div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Search Strategy:</span>
      <select v-model="selected_search_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_search_strategies" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Tokenizer:</span>
      <select v-model="selected_tokenizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_tokenizer" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Vectorizer:</span>
      <select v-model="selected_vectorizer" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_vectorizers" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Cluster Title Strategy:</span>
      <select v-model="selected_cluster_title_strategy" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in available_cluster_title_strategies" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Dim. Red. Shape:</span>
      <select v-model="dim_reducer_parameters.shape.value" class="w-1/2 pl-2 pr-8 pt-1 pb-1 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
          <option v-for="item in dim_reducer_parameters.shape.options" :value="item.id" selected>{{ item.title }}</option>
      </select>
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">UMAP n_neighbors:</span>
      <span class="text-gray-500 text-sm"> {{ dim_reducer_parameters.n_neighbors.value }} </span>
      <input v-model.number="dim_reducer_parameters.n_neighbors.value" type="range" min="1" max="100" step="1" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">UMAP min_dist:</span>
      <span class="text-gray-500 text-sm"> {{ dim_reducer_parameters.min_dist.value }} </span>
      <input v-model.number="dim_reducer_parameters.min_dist.value" type="range" min="0.001" max="0.2" step="0.001" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">UMAP n_epochs:</span>
      <span class="text-gray-500 text-sm"> {{ dim_reducer_parameters.n_epochs.value }} </span>
      <input v-model.number="dim_reducer_parameters.n_epochs.value" type="range" min="10" max="3000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">UMAP metric:</span>
      <input v-model.number="dim_reducer_parameters.metric.value" class="w-1/2 text-gray-500 text-sm">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Max. items for map:</span>
      <span class="text-gray-500 text-sm"> {{ max_items_used_for_mapping }} </span>
      <input v-model.number="max_items_used_for_mapping" type="range" min="10" max="10000" step="10" class="w-1/2 h-2 bg-gray-100 rounded-lg appearance-none cursor-pointer">
    </div>
    <div class="flex justify-between items-center">
      <span class="text-gray-500 text-sm">Show timings:</span>
      <input v-model="show_timings" type="checkbox">
    </div>
  </div>
</template>
