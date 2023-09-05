import { defineStore } from 'pinia'

export const useAppStateStore = defineStore('appState', {
  state: () => {
    return {
      settings: {
        schema_id: null,
        search_settings: {
          query: "",
          search_vector_field: null,
          search_strategy: "typesense",
          result_list_items_per_page: 10,
          result_list_current_page: 0,
          result_list_max_pages: 20,  // needed?
          max_items_used_for_mapping: 2000,
        },
        vectorize_settings: {
          map_vector_field: null,
          tokenizer: "default",
          vectorizer: "pubmedbert",
        },
        projection_settings: {
          shape: "2d",
          n_neighbors: 15,
          min_dist: 0.05,
          n_epochs: 500,
          metric: "euclidean",
          dim_reducer: "umap",
        },
        render_settings: {
          clusterizer_parameters: {
            min_cluster_size: "auto",
            min_samples: 5,
            clusterizer: "hdbscan",
            cluster_title_strategy: "tf_idf_top_3",
          },
        },
      },
      available_vector_fields: [],
    }
  },
})
