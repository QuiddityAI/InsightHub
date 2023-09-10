import { defineStore } from 'pinia'

export const useAppStateStore = defineStore('appState', {
  state: () => {
    return {
      show_timings: false,
      settings: {
        schema_id: null,
        search: {
          search_type: "external_input",  // or cluster, collection or similar item
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          combined_search_strategy: "hybrid",
          separate_queries: {},

          // list results:
          result_list_items_per_page: 10,
          result_list_current_page: 0,

          // map results:
          max_items_used_for_mapping: 2000,
        },
        vectorize: {
          map_vector_field: null,
          tokenizer: "default",
          use_w2v_model: false,
          vectorizer: "pubmedbert",  // deprecated
        },
        projection: {
          shape: "2d",
          n_neighbors: 15,
          min_dist: 0.05,
          n_epochs: 500,
          metric: "euclidean",
          dim_reducer: "umap",
        },
        rendering: {
          point_size_field: null,
          point_color_field: 'cluster',
          show_thumbnails: true,
          clusterizer_parameters: {
            min_cluster_size: "auto",
            min_samples: 5,
            clusterizer: "hdbscan",
            cluster_title_strategy: "tf_idf_top_3",
          },
        },
      },
      available_vector_fields: [],
      available_number_fields: [],
    }
  },
})
