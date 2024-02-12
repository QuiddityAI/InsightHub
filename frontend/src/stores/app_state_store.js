import { defineStore } from "pinia"
import { inject } from "vue"
import cborJs from "https://cdn.jsdelivr.net/npm/cbor-js@0.1.0/+esm"

import httpClient from "../api/httpClient"

import { FieldType, normalizeArray, normalizeArrayMedianGamma } from "../utils/utils"
import { useMapStateStore } from "./map_state_store"

export const useAppStateStore = defineStore("appState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      mapState: useMapStateStore(),

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

      available_organizations: [],
      organization_id: null,
      organization: null,
      datasets: {},

      logged_in: false,
      username: null,

      // results:
      search_result_ids: [],
      search_result_items: {},
      result_list_rendering: {},
      map_id: null,
      map_data: null,
      map_item_details: [],
      cluster_data: [],
      clusterIdsPerPoint: [],

      search_result_score_info: null,
      search_timings: "",
      map_timings: "",

      // mapping progress:
      map_is_in_progess: false,
      show_loading_bar: false,
      map_viewport_is_adjusted: false,
      progress: 0.0,
      progress_step_title: "",
      fields_already_received: new Set(),

      // selection:
      selectedDocumentIdx: -1,
      selectedDocumentDetails: null,

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
            if (that.organization.default_dataset_selection.includes(dataset_id) || that.organization.default_dataset_selection.length == 0) {
              if (!that.settings.dataset_ids.includes(dataset_id)) {
                that.settings.dataset_ids.push(dataset_id)
                // FIXME: should be triggered automatically
                that.on_selected_datasets_changed()
              }
            }
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
    reset_search_results_and_map(params = { leave_map_unchanged: false }) {
      // results:
      this.search_result_ids = []
      this.search_result_items = {}
      this.map_task_id = null
      this.map_item_details = []
      this.cluster_data = []
      this.clusterIdsPerPoint = []
      this.highlighted_item_id = null
      this.selected_item_id = null
      this.highlighted_cluster_id = null
      this.selected_cluster_id = null
      this.mapState.visited_point_indexes = []

      this.search_result_score_info = null
      if (this.score_info_chart) this.score_info_chart.destroy()
      this.score_info_chart = null
      this.map_timings = []
      this.search_timings = []

      // mapping progress:
      this.map_viewport_is_adjusted = false
      this.show_loading_bar = false
      this.map_viewport_is_adjusted = false
      this.progress = 0.0
      this.progress_step_title = ""
      this.fields_already_received = new Set()

      // map:
      if (!params.leave_map_unchanged) {
        this.eventBus.emit("reset_map")
      }

      // selection:
      this.selectedDocumentIdx = -1
      this.selectedDocumentDetails = null
    },
    reset_search_box() {
      this.settings.search.search_type = "external_input"
      this.settings.search.use_separate_queries = false
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = ""

      this.settings.search.cluster_origin_map_id = null
      this.settings.search.cluster_id = null
      this.settings.search.classifier_id = null
      this.settings.search.similar_to_item_id = null

      this.settings.projection = JSON.parse(
        JSON.stringify(this.default_settings.projection)
      )
      this.settings.rendering = JSON.parse(
        JSON.stringify(this.default_settings.rendering)
      )
    },
    run_search_from_history(history_item) {
      this.settings = history_item.parameters
      this.request_search_results()
    },
    request_search_results() {
      const that = this
      if (this.settings.dataset_ids.length === 0) return

      if (
        this.settings.search.search_type == "external_input" &&
        !this.settings.search.use_separate_queries &&
        !this.settings.search.all_field_query
      ) {
        this.reset_search_results_and_map()
        return
      }

      this.reset_search_results_and_map({ leave_map_unchanged: true })
      this.eventBus.emit("map_regenerate_attribute_arrays_from_fallbacks")
      this.eventBus.emit("show_results_tab")

      this.add_search_history_item()

      httpClient
        .post(
          `/data_backend/search_list_result?ignore_cache=${this.ignore_cache}`,
          this.settings
        )
        .then(function (response) {
          that.show_received_search_results(response.data)
          that.request_map()
        })
    },
    get_current_map_name() {
      let entry_name = ""
      if (this.settings.search.search_type == "external_input") {
        if (this.settings.search.use_separate_queries) {
          entry_name = "TODO: separate fields"
        } else {
          entry_name = this.settings.search.all_field_query
          if (this.settings.search.all_field_query_negative) {
            entry_name =
              entry_name + ` (-${this.settings.search.all_field_query_negative})`
          }
        }
      } else if (this.settings.search.search_type == "cluster") {
        entry_name = `<i>Cluster</i> '${this.settings.search.origin_display_name}'`
      } else if (this.settings.search.search_type == "similar_to_item") {
        entry_name = `<i>Similar to</i> '${this.settings.search.origin_display_name}'`
      } else if (this.settings.search.search_type == "classifier") {
        entry_name = `<i>Classifier</i> '${this.settings.search.origin_display_name}'`
      } else if (
        this.settings.search.search_type == "recommended_for_classifier"
      ) {
        entry_name = `<i>Recommended for classifier</i> '${this.settings.search.origin_display_name}'`
      }
      return entry_name
    },
    add_search_history_item() {
      const that = this
      if (!this.store_search_history) return

      if (
        this.search_history.length > 0 &&
        JSON.stringify(this.search_history[this.search_history.length - 1].parameters) ==
          JSON.stringify(this.settings)
      ) {
        // -> same query as before, don't save this duplicate:
        return
      }

      const entry_name = this.get_current_map_name()
      if (!entry_name) return

      const history_item_body = {
        dataset_id: this.settings.dataset_id,
        name: entry_name,
        parameters: this.settings,
      }

      httpClient
        .post("/org/data_map/add_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history.push(response.data)
        })
    },
    show_received_search_results(response_data) {
      this.search_result_ids = response_data["sorted_ids"]
      this.search_result_items = response_data["items_by_dataset"]
      this.search_timings = response_data["timings"]
    },
    request_map() {
      const that = this
      if (this.settings.dataset_ids.length === 0) return

      httpClient
        .post(
          `/data_backend/map?ignore_cache=${this.ignore_cache}`,
          this.settings
        )
        .then(function (response) {
          that.map_id = response.data["map_id"]
          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.request_mapping_progress()
        })
    },
    request_mapping_progress() {
      const that = this

      if (!this.map_id || !this.map_is_in_progess) return

      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("map_id") != this.map_id) {
        queryParams.set("map_id", this.map_id)
        history.pushState(null, null, "?" + queryParams.toString())
      }

      // note: these may be needed in the future, pay attention to remove them in this case here
      const not_needed = [
        "item_ids",
        "raw_projections",
        "search_result_meta_information",
        "parameters",
      ]
      if (!that.debug_autocut) {
        not_needed.push("search_result_score_info")
      }

      const payload = {
        map_id: this.map_id,
        exclude_fields: not_needed.concat(Array.from(this.fields_already_received)),
      }
      const cborConfig = {
        headers: { Accept: "application/cbor" },
        responseType: "arraybuffer",
      }
      const jsonConfig = {
        headers: { Accept: "application/json" },
      }
      httpClient
        .post("/data_backend/map/result", payload, cborConfig)
        .then(function (response) {
          that.process_map_update(response)
        })
        .catch(function (error) {
          if (error.response && error.response.status === 404) {
            // no more data for this task, stop polling:
            that.map_is_in_progess = false
            console.log("404 response")
          } else {
            console.log(error)
          }
        })
        .finally(function () {
          setTimeout(
            function () {
              that.request_mapping_progress()
            }.bind(this),
            100
          )
        })
    },
    process_map_update(response) {
      const that = this
      const content_type = response.headers["content-type"]
      const data =
        content_type == "application/cbor" ? cborJs.decode(response.data) : response.data
      that.map_data = data

      if (data["finished"]) {
        // no need to get further results:
        that.map_is_in_progess = false
      }

      const progress = data["progress"]

      that.show_loading_bar = !progress.embeddings_available
      that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
      that.progress_step_title = progress.step_title

      const results = data["results"]
      if (results) {
        const results_per_point = results["per_point_data"]
        if (
          results_per_point["hover_label_data"] &&
          results_per_point["hover_label_data"].length > 0
        ) {
          that.map_item_details = results_per_point["hover_label_data"]
          that.mapState.per_point.text_data =
            results_per_point["hover_label_data"]
          that.search_result_ids = results_per_point["hover_label_data"]  // FIXME
          that.search_result_items = results_per_point["hover_label_data"]
          that.fields_already_received.add("hover_label_data")
        }

        // TODO: restore good gamma corrections:
        // that.mapState.per_point.size = normalizeArrayMedianGamma(results_per_point["size"], 2.0)
        // that.mapState.saturation = normalizeArrayMedianGamma(results_per_point["sat"], 3.0, 0.001)

        for (const attr of [
          "size",
          "hue",
          "sat",
          "val",
          "opacity",
          "secondary_hue",
          "secondary_sat",
          "secondary_val",
          "secondary_opacity",
          "flatness",
        ]) {
          if (results_per_point[attr] && results_per_point[attr].length > 0) {
            const attr_params = that.settings.rendering[attr]
            if (
              ["hue", "secondary_hue"].includes(attr) &&
              (["cluster_idx", "origin_query_idx"].includes(attr_params.type) ||
                (attr_params.type == "number_field" &&
                  that.datasets[that.settings.dataset_ids[0]].object_fields[attr_params.parameter]  // FIXME: only valid for first dataset
                    .field_type == FieldType.INTEGER))
            ) {
              // if an integer value is assigned to a hue value, we need to make sure that the last value doesn't have
              // the same hue as the first value:
              results_per_point[attr].push(Math.max(...results_per_point[attr]) + 1)
              that.mapState.per_point[attr] = normalizeArrayMedianGamma(
                results_per_point[attr],
                2.0
              ).slice(0, results_per_point[attr].length - 1)
            } else {
              that.mapState.per_point[attr] = normalizeArrayMedianGamma(
                results_per_point[attr],
                2.0
              )
            }
            that.fields_already_received.add(attr)
          }
        }

        if (
          results_per_point["cluster_ids"] &&
          results_per_point["cluster_ids"].length > 0
        ) {
          that.mapState.per_point.cluster_id = results_per_point["cluster_ids"]
          that.clusterIdsPerPoint = results_per_point["cluster_ids"]
          that.fields_already_received.add("cluster_ids")
        } else if (!that.fields_already_received.has("cluster_ids")) {
          that.mapState.per_point.cluster_id = Array(
            that.mapState.per_point.x.length
          ).fill(-1)
        }

        let should_update_geometry = false
        if (
          results_per_point["positions_x"] &&
          results_per_point["positions_x"].length > 0
        ) {
          that.mapState.per_point.x = results_per_point["positions_x"]
          should_update_geometry = true
        }
        if (
          results_per_point["positions_y"] &&
          results_per_point["positions_y"].length > 0
        ) {
          that.mapState.per_point.y = results_per_point["positions_y"]
          should_update_geometry = true
        }
        if (should_update_geometry) {
          that.eventBus.emit("map_update_geometry")
        }

        if (
          results["thumbnail_atlas_filename"] &&
          results["thumbnail_atlas_filename"] !== "loading"
        ) {
          const image = new Image()
          image.src =
            "data_backend/map/thumbnail_atlas/" + results["thumbnail_atlas_filename"]
          image.onload = () => {
            that.mapState.textureAtlas = image
            that.mapState.thumbnailSpriteSize = results["thumbnail_sprite_size"]
            that.eventBus.emit("map_update_geometry")
          }
          that.fields_already_received.add("thumbnail_atlas_filename")
          that.settings.frontend.rendering.point_size_factor = 3.0
          that.settings.frontend.rendering.max_opacity = 1.0
        } else if (
          results["thumbnail_atlas_filename"] &&
          results["thumbnail_atlas_filename"] === "loading"
        ) {
          that.mapState.textureAtlas = null
        }

        if (results["clusters"] && Object.keys(results["clusters"]).length > 0) {
          that.mapState.clusterData = results["clusters"]
          that.cluster_data = results["clusters"]
          that.fields_already_received.add("clusters")
        }

        if (that.map_viewport_is_adjusted) {
          that.eventBus.emit("map_center_and_fit_data_to_active_area_smooth")
        } else {
          that.eventBus.emit("map_reset_pan_and_zoom")
          that.eventBus.emit("map_center_and_fit_data_to_active_area_instant")
          that.map_viewport_is_adjusted = true
        }

        if (results["search_result_score_info"]) {
          that.search_result_score_info = results["search_result_score_info"]
          that.fields_already_received.add("search_result_score_info")
          that.eventBus.emit("show_score_info_chart")
        }

        that.map_timings = results["timings"]
      }
    },
    narrow_down_on_cluster(cluster_item) {
      this.settings.search.search_type = "cluster"
      this.settings.search.cluster_origin_map_id = this.map_id
      this.settings.search.cluster_id = cluster_item.id
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = cluster_item.title
      this.request_search_results()
    },
    show_classifier_as_map(classifier) {
      this.settings.search.search_type = "classifier"
      this.settings.search.classifier_id = classifier.id
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = classifier.name
      this.request_search_results()
    },
    recommend_items_for_classifier(classifier) {
      this.settings.search.search_type = "recommended_for_classifier"
      this.settings.search.classifier_id = classifier.id
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = classifier.name
      this.request_search_results()
    },
    show_global_map() {
      this.settings.search.search_type = "global_map"
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.request_search_results()
    },
    show_document_details(pointIdx) {
      this.selectedDocumentIdx = pointIdx
      this.mapState.markedPointIdx = pointIdx
      this.mapState.visited_point_indexes.push(pointIdx)
      this.mapState.per_point.flatness[pointIdx] = 1.0
      that.eventBus.emit("map_update_geometry")
    },
    show_document_details_by_id(item_id) {
      for (const i of Array(this.map_item_details.length).keys()) {
        if (this.map_item_details[i]._id == item_id) {
          this.selectedDocumentIdx = i
          this.mapState.markedPointIdx = i
          break
        }
      }
    },
    showSimilarItems() {
      this.settings.search.search_type = "similar_to_item"
      this.settings.search.similar_to_item_id =
        this.map_item_details[this.selectedDocumentIdx]._id
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.projection.use_polar_coordinates = true
      this.settings.projection.x_axis = { type: "score", parameter: "" }
      this.settings.projection.y_axis = {
        type: "umap",
        parameter: "primary",
      }
      const title_func = this.mapState.hover_label_rendering.title
      this.settings.search.origin_display_name = title_func(
        this.map_item_details[this.selectedDocumentIdx]
      )
      this.request_search_results()
    },
    close_document_details() {
      this.selectedDocumentIdx = -1
      this.mapState.markedPointIdx = -1
      this.selectedDocumentDetails = null
    },
    store_current_map() {
      const that = this
      const entry_name = this.get_current_map_name()
      if (!entry_name) return
      const store_map_body = {
        dataset_id: this.settings.dataset_id,
        name: entry_name,
        map_id: this.map_id,
      }
      httpClient.post("/data_backend/map/store", store_map_body).then(function (response) {
        that.stored_maps.push(response.data)
      })
    },
    delete_stored_map(stored_map_id) {
      const that = this
      const delete_stored_map_body = {
        stored_map_id: stored_map_id,
      }
      httpClient
        .post("/org/data_map/delete_stored_map", delete_stored_map_body)
        .then(function (response) {
          const index_to_be_removed = that.stored_maps.findIndex((item) => item.id === stored_map_id)
          if (index_to_be_removed !== null) {
            that.stored_maps.splice(index_to_be_removed, 1)
          }
        })
    },
    show_stored_map(stored_map_id) {
      // console.log("showing stored map", stored_map_id)
      const that = this

      that.map_id = stored_map_id
      const body = {
        map_id: this.map_id,
      }
      this.reset_search_results_and_map()
      this.eventBus.emit("show_results_tab")

      httpClient
        .post("/data_backend/stored_map/parameters_and_search_results", body)
        .then(function (response) {
          const parameters = response.data.parameters
          that.settings = parameters
          that.eventBus.emit("map_regenerate_attribute_arrays_from_fallbacks")

          // now done when map results are received
          //that.show_received_search_results(response.data)

          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.request_mapping_progress()
        })
    },
    add_selected_points_to_classifier(classifier_id, class_name, is_positive) {
      // TODO: implement more efficient way
      for (const point_index of this.mapState.selected_point_indexes) {
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
      for (const point_index of this.mapState.selected_point_indexes) {
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
