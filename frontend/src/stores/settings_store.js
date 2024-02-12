import { defineStore } from "pinia"
import { inject } from "vue"

import httpClient from "../api/httpClient"

import { FieldType } from "../utils/utils"

export const useAppStateStore = defineStore("appState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),

      show_timings: false,
      store_search_history: true,
      ignore_cache: false,
      debug_autocut: false,

      highlighted_item_id: null,
      selected_item_id: null,
      highlighted_cluster_id: null,
      selected_cluster_id: null,
      selected_map_tool: "drag", // one of 'drag' or 'lasso'
      selection_merging_mode: "replace", // one of 'replace', 'add', 'remove'
      selected_point_indexes: [],
      visited_point_indexes: [],

      available_vector_fields: [],
      available_number_fields: [],

      available_organizations: [],
      organization_id: null,
      organization: null,
      datasets: {},
      dataset: null,
      map_data: null,

      logged_in: false,
      username: null,

      // classifiers:
      classifiers: [],
      last_used_classifier_id: null,
      classifier_example_rendering: {},

      search_history: [],
      stored_maps: [],

      settings: {
        dataset_ids: [],
        dataset_id: null, // deprecated, use dataset_ids instead
        search: {
          search_type: "external_input", // or cluster, classifier or similar item
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          internal_input_weight: 0.7,
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

          origin_display_name: "", // classifier or cluster name, that this map refers to, just for displaying it
          cluster_origin_map_id: null,
          cluster_id: null,
          classifier_id: null,
          similar_to_item_id: null,

          // list results:
          result_list_items_per_page: 10,
          result_list_current_page: 0,

          // map results:
          max_items_used_for_mapping: 2000,
          thumbnail_sprite_size: "auto",
        },
        vectorize: {
          map_vector_field: "w2v_vector",
          secondary_map_vector_field: null,
          tokenizer: "default",
        },
        projection: {
          x_axis: { type: "umap", parameter: "primary" }, // type options: umap (primary / secondary), number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], fulltext_score
          y_axis: { type: "umap", parameter: "primary" }, // type options: umap (primary / secondary), number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], fulltext_score
          n_neighbors: 15,
          min_dist: 0.17,
          n_epochs: 500,
          metric: "euclidean",
          dim_reducer: "umap",
          use_polar_projection: false,
          invert_x_axis: false,
        },
        rendering: {
          size: { type: "score", parameter: "" }, // type options: fixed / static, number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], fulltext_score, origin_query_idx, cluster_idx, contains (field, tag / class), is_empty (field)
          hue: { type: "cluster_idx", parameter: "" },
          sat: { type: "score", parameter: "" },
          val: { type: "fixed", parameter: "" },
          opacity: { type: "fixed", parameter: "" },
          secondary_hue: { type: "fixed", parameter: "" },
          secondary_sat: { type: "fixed", parameter: "" },
          secondary_val: { type: "fixed", parameter: "" },
          secondary_opacity: { type: "fixed", parameter: "" },
          flatness: { type: "fixed", parameter: "" },
          enable_clustering: true,
          clusterizer_parameters: {
            min_cluster_size: -1,
            min_samples: 5,
            leaf_mode: false,
            clusterizer: "hdbscan",
          },
          cluster_title_strategy: "tf_idf_top_3",
        },
        frontend: {
          // included here to be able to be restored using map_id (stored in backend)
          rendering: {
            show_thumbnails: true,
            show_cluster_titles: true,
            size: { min: 0.0, max: 1.0, fallback: 0.5, gamma: "auto", threshold: null }, // TODO: store debounced after change
            hue: { min: 0.0, max: 1.0, fallback: 0.0, gamma: "auto", threshold: null },
            sat: { min: 0.0, max: 1.0, fallback: 0.7, gamma: "auto", threshold: null },
            val: { min: 0.0, max: 1.0, fallback: 0.7, gamma: "auto", threshold: null },
            opacity: { min: 0.0, max: 1.0, fallback: 1.0, gamma: "auto", threshold: null },
            secondary_hue: {
              min: 0.0,
              max: 1.0,
              fallback: 0.0,
              gamma: "auto",
              threshold: null,
            },
            secondary_sat: {
              min: 0.0,
              max: 1.0,
              fallback: 1.0,
              gamma: "auto",
              threshold: null,
            },
            secondary_val: {
              min: 0.0,
              max: 1.0,
              fallback: 1.0,
              gamma: "auto",
              threshold: null,
            },
            secondary_opacity: {
              min: 0.0,
              max: 1.0,
              fallback: 0.0,
              gamma: "auto",
              threshold: null,
            },
            flatness: { min: 0.0, max: 1.0, fallback: 0.0, gamma: "auto", threshold: null },
            max_opacity: 0.7,
            shadow_opacity: 1.0,
            point_size_factor: 1.0,
            style: "3d", // one of "3d", "plotly"
          },
        },
      },

      // exactly the same settings again to be able to restore them later on:
      // (not initializing the actual settings from this because of autocomplete)
      // (initialized in initialize())
      default_settings: null,
    }
  },
  actions: {
    initialize() {
      this.default_settings = JSON.parse(JSON.stringify(this.settings))
    },
    retrieve_current_user() {
      const that = this
      httpClient.get("/org/data_map/get_current_user").then(function (response) {
        that.logged_in = response.data.logged_in
        that.username = response.data.username
      })
    },
    retrieve_stored_maps_history_and_classifiers() {
      const that = this
      this.search_history = []
      // FIXME: refactor with organization_id
      const get_history_body = {
        dataset_id: this.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_search_history", get_history_body)
        .then(function (response) {
          that.search_history = response.data
        })

      this.classifiers = []
      const get_classifiers_body = {
        dataset_id: this.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_classifiers", get_classifiers_body)
        .then(function (response) {
          that.classifiers = response.data
        })

      this.stored_maps = []
      const get_stored_maps_body = {
        dataset_id: this.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_stored_maps", get_stored_maps_body)
        .then(function (response) {
          that.stored_maps = response.data
        })
    },
    retrieve_available_organizations(on_success = null) {
      const that = this
      httpClient.post("/org/data_map/available_organizations", {}).then(function (response) {
        that.available_organizations = response.data
        // initial organization_id is set in evaluate_url_query_parameters() in SearchAndMap
        if (on_success) {
          on_success()
        }
      })
    },
    set_organization_id(organization_id, change_history = true) {
      this.organization_id = organization_id
      this.organization = this.available_organizations.find(
        (item) => item.id === organization_id
      )

      const clean_settings = JSON.parse(JSON.stringify(this.default_settings))
      this.settings = clean_settings

      if (change_history) {
        const emptyQueryParams = new URLSearchParams()
        emptyQueryParams.set("organization_id", this.organization_id)
        history.pushState(null, null, "?" + emptyQueryParams.toString())
      }

      this.retrieve_available_datasets()
    },
    retrieve_available_datasets() {
      const that = this
      this.datasets = {}

      for (const dataset_id of this.organization.datasets) {
        httpClient
          .post("/org/data_map/dataset", { dataset_id: dataset_id })
          .then(function (response) {
            const dataset = response.data

            // convert strings to functions:
            const result_list_rendering = dataset.result_list_rendering
            for (const field of ["title", "subtitle", "body", "image", "url"]) {
              result_list_rendering[field] = eval(result_list_rendering[field])
            }
            dataset.result_list_rendering = result_list_rendering

            const classifier_example_rendering = dataset.classifier_example_rendering
            for (const field of ["title", "subtitle", "body", "image", "url"]) {
              classifier_example_rendering[field] = eval(classifier_example_rendering[field])
            }
            dataset.classifier_example_rendering = classifier_example_rendering

            const hover_label_rendering = dataset.hover_label_rendering
            for (const field of ["title", "subtitle", "body", "image"]) {
              hover_label_rendering[field] = hover_label_rendering[field]
                ? eval(hover_label_rendering[field])
                : (item) => ""
            }
            dataset.hover_label_rendering = hover_label_rendering

            that.datasets[dataset_id] = dataset
            if (!that.settings.dataset_ids.includes(dataset_id)) {
              that.settings.dataset_ids.push(dataset_id)
            }
            // FIXME: should be triggered automatically
            that.on_selected_datasets_changed()
          })
      }
    },
    on_selected_datasets_changed() {
      this.populate_search_fields_based_on_selected_datasets()
    },
    populate_search_fields_based_on_selected_datasets() {
      const that = this
      this.settings.search.separate_queries = {}

      for (const dataset_id of this.settings.dataset_ids) {
        const dataset = this.datasets[dataset_id]

        // initialize available search fields:
        for (const field of Object.values(dataset.object_fields)) {
          if (field.is_available_for_search) {
            that.settings.search.separate_queries[field.identifier] = {
              query: "",
              query_negative: "",
              must: false,
              threshold_offset: 0.0,
              use_for_combined_search: dataset.default_search_fields.includes(
                field.identifier
              ),
            }
          }
        }

        // initialize available number and vector fields:
        that.settings.vectorize.map_vector_field = "w2v_vector"
        that.available_vector_fields = []
        that.available_number_fields = []
        for (const field_identifier in dataset.object_fields) {
          const field = dataset.object_fields[field_identifier]
          if (field.field_type == FieldType.VECTOR) {
            that.available_vector_fields.push(field.identifier)
            if (
              field.is_available_for_search &&
              dataset.default_search_fields.includes(field.identifier)
            ) {
              that.settings.vectorize.map_vector_field = field.identifier
            }
          } else if (
            field.field_type == FieldType.INTEGER ||
            field.field_type == FieldType.FLOAT
          ) {
            that.available_number_fields.push(field.identifier)
          }
        }
        that.settings.rendering.size.type = "score"
        that.settings.rendering.size.parameter = ""
        if (that.available_number_fields.length > 0) {
          for (const field of that.available_number_fields) {
            if (field === "cited_by_count") {
              // prefer this field even if it is not the first one:
              that.settings.rendering.size.type = "number_field"
              that.settings.rendering.size.parameter = field
              break
            }
          }
        }
      }
    },
    add_selected_points_to_classifier(classifier_id, class_name, is_positive) {
      // TODO: implement more efficient way
      for (const point_index of this.selected_point_indexes) {
        this.add_item_to_classifier(point_index, classifier_id, class_name, is_positive)
      }
    },
    add_item_to_classifier(item_index, classifier_id, class_name, is_positive) {
      const that = this
      const classifier =
        this.classifiers[this.classifiers.findIndex((e) => e.id == classifier_id)]
      if (!classifier) return

      this.last_used_classifier_id = classifier.id
      const item_id = this.map_data.results.per_point_data.hover_label_data[item_index]._id
      const add_item_to_classifier_body = {
        classifier_id: classifier.id,
        is_positive: is_positive,
        class_name: class_name,
        field_type: FieldType.IDENTIFIER,
        value: item_id,
        weight: 1.0,
      }
      httpClient
        .post("/org/data_map/add_item_to_classifier", add_item_to_classifier_body)
        .then(function (created_item) {
          const class_details = classifier.actual_classes.find(
            (actual_class) => actual_class.name === class_name
          )
          class_details[is_positive ? "positive_count" : "negative_count"] += 1
          that.eventBus.emit("classifier_example_added", {
            classifier_id: classifier.id,
            class_name,
            is_positive,
            created_item: created_item.data,
          })
        })
    },
    remove_selected_points_from_classifier(classifier_id, class_name) {
      // TODO: implement more efficient way
      for (const point_index of this.selected_point_indexes) {
        this.remove_item_from_classifier(point_index, classifier_id, class_name)
      }
    },
    remove_item_from_classifier(item_index, classifier_id, class_name) {
      const that = this
      const item_id = this.map_data.results.per_point_data.hover_label_data[item_index]._id
      const body = {
        classifier_id: classifier_id,
        class_name: class_name,
        value: item_id,
      }
      httpClient
        .post("/org/data_map/remove_classifier_example_by_value", body)
        .then(function (response) {
          for (const item of response.data) {
            const classifier_example_id = item.id
            that.eventBus.emit("classifier_example_removed", {
              classifier_id,
              class_name,
              classifier_example_id,
            })
            const classifier = that.classifiers.find(
              (classifier) => classifier.id === classifier_id
            )
            const class_details = classifier.actual_classes.find(
              (actual_class) => actual_class.name === class_name
            )
            class_details[item.is_positive ? "positive_count" : "negative_count"] -= 1
          }
        })
    },
  },
})
