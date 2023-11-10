import { defineStore } from 'pinia'

export const useAppStateStore = defineStore('appState', {
  state: () => {
    return {
      show_timings: false,
      store_search_history: true,
      ignore_cache: false,
      debug_autocut: false,

      highlighted_item_id: null,
      selected_item_id: null,
      highlighted_cluster_id: null,
      selected_cluster_id: null,

      available_vector_fields: [],
      available_number_fields: [],

      dataset: null,

      // collections:
      collections: [],
      last_used_collection_id: null,
      collection_list_rendering: {},

      settings: {
        dataset_id: null,
        search: {
          search_type: "external_input",  // or cluster, collection or similar item
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          use_similarity_thresholds: true,
          use_autocut: true,
          autocut_strategy: "knee_point",
          autocut_min_results: 10,
          autocut_min_score: 0.1,
          autocut_max_relative_decline: 1.0,
          separate_queries: {
            // for each search field:
            // query: "",
            // query_negative: "",
            // must: false,
            // threshold_offset: 0.0,
            // use_for_combined_search: that.dataset.default_search_fields.includes(field.identifier),
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
          thumbnail_sprite_size: "auto",
        },
        vectorize: {
          map_vector_field: null,
          tokenizer: "default",
        },
        projection: {
          shape: "2d",
          n_neighbors: 15,
          min_dist: 0.17,
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

      // exactly the same settings again to be able to restore them later on:
      // (not initializing the actual settings from this because of autocomplete)
      default_settings: {
        dataset_id: null,
        search: {
          search_type: "external_input",  // or cluster, collection or similar item
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          use_similarity_thresholds: true,
          use_autocut: true,
          autocut_strategy: "knee_point",
          autocut_min_results: 10,
          autocut_min_score: 0.1,
          autocut_max_relative_decline: 1.0,
          separate_queries: {
            // for each search field:
            // query: "",
            // query_negative: "",
            // must: false,
            // threshold_offset: 0.0,
            // use_for_combined_search: that.dataset.default_search_fields.includes(field.identifier),
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
          thumbnail_sprite_size: 64,
        },
        vectorize: {
          map_vector_field: null,
          tokenizer: "default",
        },
        projection: {
          shape: "2d",
          n_neighbors: 15,
          min_dist: 0.17,
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
    }
  },
})
