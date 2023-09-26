import { defineStore } from 'pinia'

export const useAppStateStore = defineStore('appState', {
  state: () => {
    return {
      show_timings: false,
      store_search_history: true,
      selected_cluster_title: null,
      selected_collection_title: null,
      ignore_cache: false,
      settings: {
        schema_id: null,
        search: {
          search_type: "external_input",  // or cluster, collection or similar item
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          separate_queries: {
            // for each search field:
            // query: "",
            // query_negative: "",
            // must: false,
            // threshold_offset: 0.0,
            // use_for_combined_search: that.schema.default_search_fields.includes(field.identifier),
          },

          origin_display_name: "", // collection or cluster name, that this map refers to, just for displaying it
          cluster_origin_map_id: null,
          cluster_id: null,
          collection_id: null,
          similar_to_item_id: null,

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
          point_size: null,
          point_color: 'cluster',
          show_thumbnails: true,
          clusterizer_parameters: {
            min_cluster_size: -1,
            min_samples: 5,
            leaf_mode: false,
            clusterizer: "hdbscan",
          },
          cluster_title_strategy: "tf_idf_top_3",
        },
      },
      available_vector_fields: [],
      available_number_fields: [],
    }
  },
})
