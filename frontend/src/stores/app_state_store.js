import { defineStore } from "pinia"
import { inject } from "vue"
import { decode as cborDecode } from 'cbor-x';
import { useToast } from "primevue/usetoast"

import { httpClient } from "../api/httpClient"

import { FieldType, normalizeArray, normalizeArrayMedianGamma } from "../utils/utils"
import { useMapStateStore } from "./map_state_store"

export const useAppStateStore = defineStore("appState", {
  state: () => {
    return {
      eventBus: inject("eventBus"),
      toast: useToast(),
      mapState: useMapStateStore(),

      available_organizations: [],
      organization_id: null,
      organization: null,
      datasets: {},

      user_id: null,
      logged_in: false,
      username: null,
      dev_mode: false,

      selected_app_tab: "collections",

      show_timings: false,
      store_search_history: true,
      ignore_cache: false,
      debug_autocut: false,
      show_error_dialog: false,
      error_dialog_message: "",
      load_map_after_search: true,

      highlighted_item_id: null,
      highlighted_cluster_id: null,
      selected_cluster_id: null,

      available_vector_fields: [],
      available_number_fields: [],
      available_language_filters: [],
      available_ranking_options: [],
      last_used_language: "en",

      // results:
      is_loading_search_results: false,
      search_result_ids: [],
      visible_result_ids : [],
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
      extended_search_results_are_loading: false,
      show_loading_bar: false,
      map_viewport_is_adjusted: false,
      progress: 0.0,
      progress_step_title: "",
      fields_already_received: new Set(),
      last_position_update_received: null,

      // selection:
      selected_document_ds_and_id: null,  // (dataset_id, item_id)
      selected_document_relevant_parts: [],
      selected_document_query: "",
      selected_document_initial_item: null,
      document_details_dialog_is_visible: false,

      // collections:
      collections: [],
      last_used_collection_id: null,
      last_used_collection_class: null,

      // chats:
      chats: [],

      search_history: [],
      stored_maps: [],

      // writing tasks:
      selected_writing_task_id: null,
      selected_writing_task: null,
      available_ai_modules: [
        { identifier: 'openai_gpt_3_5', name: 'GPT 3.5 (medium accuracy and cost)' },
        { identifier: 'openai_gpt_4_turbo', name: 'GPT 4 Turbo (highest accuracy and cost, very slow)' },
        { identifier: 'openai_gpt_4_o', name: 'GPT 4o (highest accuracy and cost, slow)' },
        { identifier: 'groq_llama_3_8b', name: 'Llama 3 8B (lowest cost, low accuracy, super fast)' },
        { identifier: 'groq_llama_3_70b', name: 'Llama 3 70B (low cost, medium accuracy, fast)' },
      ],
      column_modules: [
        { identifier: 'llm', name: 'LLM' },
        // { identifier: 'python_expression', name: 'Python Expression' },
        { identifier: 'website_scraping', name: 'Website Text Extraction' },
        { identifier: 'web_search', name: 'Web Search' },
        { identifier: 'notes', name: 'No AI, just notes' },
      ],

      settings: {
        search: {
          dataset_ids: [],
          task_type: null,  // one of quick_search, custom_search etc.
          search_type: "external_input", // or cluster, collection or similar item
          retrieval_mode: "hybrid",  // "keyword", "vector", "hybrid"
          use_separate_queries: false,
          all_field_query: "",
          all_field_query_negative: "",
          question: "",
          internal_input_weight: 0.7,
          use_similarity_thresholds: true,
          order_by: { type: "score", parameter: "" },  // not used at the moment
          auto_relax_query: true,
          use_reranking: true,
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
            // use_for_combined_search: that.dataset.schema.default_search_fields.includes(field.identifier),
          },
          filters: [
            // for each filter:
            // {
            //   field: "",  // _descriptive_text_field or any other "filterable" field name
            //   dataset_id: "",  // dataset_id of the field, for now filters are applied to all datasets, but dataset_id is needed to get the field description
            //   operator: "",  // one of is, is_not, contains, does_not_contain, gt, gte, lt, lte
            //   value: "",  // str or number value
            // },
          ],
          result_language: "en",
          ranking_settings: {},

          origin_display_name: "", // collection or cluster name, that this map refers to, just for displaying it
          origins: [],  // for each origin: { type: "cluster", display_name: "", map_id: "123" }
          cluster_origin_map_id: null,
          cluster_id: null,
          collection_id_and_class: null,
          similar_to_item_id: null,

          // list results:
          result_list_items_per_page: 10,
          result_list_current_page: 0,
          max_sub_items_per_item: 1,  // aka number of relevant chunks per item
          return_highlights: false,
          use_bolding_in_highlights: true,

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
          x_axis: { type: "embedding", parameter: "primary" }, // type options: embedding (primary / secondary), number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], keyword_score
          y_axis: { type: "embedding", parameter: "primary" }, // type options: embedding (primary / secondary), number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], keyword_score
          cluster_hints: "",
          n_neighbors: 15,
          min_dist: 0.17,
          n_epochs: 500,
          metric: "euclidean",
          dim_reducer: "umap",
          use_polar_projection: false,
          invert_x_axis: false,
        },
        rendering: {
          size: { type: "score", parameter: "" }, // type options: fixed / static, number_field (field), classifier (name), count (array field), rank, score [to query, similar item, group centroid], keyword_score, origin_query_idx, cluster_idx, contains (field, tag / class), is_empty (field)
          hue: { type: "cluster_idx", parameter: "" },
          sat: { type: "fixed", parameter: "" },
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
            max_cluster_size: 0.5,
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
            thumbnail_aspect_ratio: {
              min: -1.0,
              max: 5.0,
              fallback: -1.0,
              gamma: "auto",
              threshold: null,
            },
            max_opacity: 0.7,
            shadow_opacity: 1.0,
            point_size_factor: 1.0,
            style: "plotly", // one of "3d", "plotly"
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
      this.store_current_settings_as_default()
    },
    store_current_settings_as_default() {
      this.default_settings = JSON.parse(JSON.stringify(this.settings))
    },
    enable_simplified_absclust_user_mode() {
      this.set_organization_id(1)
      this.reset_search_box()
    },
    toggle_dev_mode() {
      this.dev_mode = !this.dev_mode
      if (this.dev_mode) {
        // do other dev things?
      } else {
        this.enable_simplified_absclust_user_mode()
      }
    },
    retrieve_current_user(on_success = null) {
      const that = this
      httpClient.get("/org/data_map/get_current_user").then(function (response) {
        that.logged_in = response.data.logged_in
        that.user = response.data
        if (on_success) {
          on_success()
        }
      })
    },
    retrieve_stored_maps_history_and_collections() {
      const that = this
      if (this.organization_id == null) {
        console.log("organization_id is null, cannot retrieve stored maps, history and collections")
        return
      }
      if (!this.logged_in) {
        console.log("not logged in, cannot retrieve stored maps, history and collections")
        return
      }
      this.search_history = []
      // FIXME: refactor with organization_id
      const get_history_body = {
        organization_id: this.organization_id,
      }
      httpClient
        .post("/org/data_map/get_search_history", get_history_body)
        .then(function (response) {
          that.search_history = response.data
        })

      this.collections = []
      const get_collections_body = {
        related_organization_id: this.organization_id,
      }
      httpClient
        .post("/org/data_map/get_collections", get_collections_body)
        .then(function (response) {
          that.collections = response.data || []
        })

      this.stored_maps = []
      const get_stored_maps_body = {
        organization_id: this.organization_id,
      }
      httpClient
        .post("/org/data_map/get_stored_maps", get_stored_maps_body)
        .then(function (response) {
          that.stored_maps = response.data
        })

      this.chats = []
      const get_chats_body = {}
      httpClient
        .post("/org/data_map/get_chats", get_chats_body)
        .then(function (response) {
          that.chats = response.data
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
    set_organization_id(organization_id, change_history = true, preselected_dataset_ids = null) {
      if (this.organization_id === organization_id) return
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

      this.retrieve_available_datasets(preselected_dataset_ids)
    },
    set_app_tab(part) {
      this.selected_app_tab = part
      // store selected part in URL:
      const queryParams = new URLSearchParams(window.location.search)
      queryParams.set("tab", part)
      history.pushState(null, null, "?" + queryParams.toString())
      umami.track(props => ({ ...props, url: part, event_type: "tab_change", title: part }))
    },
    retrieve_available_datasets(preselected_dataset_ids = null) {
      const that = this
      this.datasets = {}

      for (const dataset_id of this.organization.datasets) {
        this.fetch_dataset(dataset_id, () => {
          let selected = false
          if (preselected_dataset_ids !== null) {
            selected = preselected_dataset_ids.includes(dataset_id)
          } else if (that.organization.default_dataset_selection.includes(dataset_id) || that.organization.default_dataset_selection.length == 0) {
            selected = true
          }
          if (selected) {
            if (!that.settings.search.dataset_ids.includes(dataset_id)) {
              that.settings.search.dataset_ids.push(dataset_id)
              // FIXME: should be triggered automatically
              that.on_selected_datasets_changed()
            }
          }
          if (Object.keys(that.datasets).length == that.organization.datasets.length) {
            that.eventBus.emit("datasets_are_loaded")
          }
        })
      }
    },
    fetch_dataset(dataset_id, on_success = null) {
      const that = this
      httpClient
        .post("/org/data_map/dataset", { dataset_id: dataset_id })
        .then(function (response) {
          const dataset = response.data
          that.prepare_dataset_object(dataset)
          that.datasets[dataset_id] = dataset
          if (on_success) {
            on_success()
          }
        })
    },
    prepare_dataset_object(dataset) {
      // convert strings to functions:
      const result_list_rendering = dataset.schema.result_list_rendering
      for (const field of ["title", "subtitle", "body", "image", "url", "icon", "badges", "tagline", "sub_tagline"]) {
        // eval?.('"use strict"; ' + code) prevents access to local variables and
        // any new variable or function declarations are scoped instead of global
        // (still a major security risk, more meant to prevent accidental bugs)
        if (field === "badges" && !result_list_rendering[field]) {
          result_list_rendering["badges"] = result_list_rendering["tags"]
        }
        result_list_rendering[field] = eval?.('"use strict"; ' + result_list_rendering[field]) || ((item) => null)
      }
      dataset.schema.result_list_rendering = result_list_rendering

      const hover_label_rendering = dataset.schema.hover_label_rendering
      for (const field of ["title", "subtitle", "body", "image"]) {
        hover_label_rendering[field] = hover_label_rendering[field]
          ? eval?.('"use strict"; ' + hover_label_rendering[field])
          : (item) => ""
      }
      dataset.schema.hover_label_rendering = hover_label_rendering

      const detail_view_rendering = dataset.schema.detail_view_rendering
      for (const field of ["title", "subtitle", "body", "image", "url", "doi", "icon", "badges", "full_text_pdf_url", "tagline", "sub_tagline"]) {
        if (field === "badges" && !result_list_rendering[field]) {
          result_list_rendering["badges"] = result_list_rendering["tags"]
        }
        detail_view_rendering[field] = detail_view_rendering[field]
          ? eval?.('"use strict"; ' + detail_view_rendering[field])
          : (item) => ""
      }
      for (const link of detail_view_rendering.links || []) {
        link.url = link.url ? eval(link.url) : ""
      }
      dataset.schema.detail_view_rendering = detail_view_rendering

      return dataset
    },
    on_selected_datasets_changed() {
      // store selected datasets in URL:
      const queryParams = new URLSearchParams(window.location.search)
      queryParams.set("dataset_ids", this.settings.search.dataset_ids.join(","))
      history.replaceState(null, null, "?" + queryParams.toString())
      this.populate_search_fields_based_on_selected_datasets()
      // update default search settings:
      this.settings.search.retrieval_mode = this.settings.search.dataset_ids.map(dataset_id => this.datasets[dataset_id].merged_advanced_options.retrieval_mode).reduce((acc, val) => val == 'keyword' || val == 'meaning' ? val : acc, "hybrid")
      this.settings.frontend.rendering.max_opacity = this.default_settings.frontend.rendering.max_opacity
      this.settings.frontend.rendering.point_size_factor = this.default_settings.frontend.rendering.point_size_factor
      for (const dataset_id of this.settings.search.dataset_ids) {
        const dataset = this.datasets[dataset_id]
        if (dataset.merged_advanced_options.max_opacity != undefined) {
          this.settings.frontend.rendering.max_opacity = dataset.merged_advanced_options.max_opacity
        }
        if (dataset.merged_advanced_options.point_size_factor != undefined) {
          this.settings.frontend.rendering.point_size_factor = dataset.merged_advanced_options.point_size_factor
        }
      }
    },
    populate_search_fields_based_on_selected_datasets() {
      const that = this
      this.settings.search.separate_queries = {}
      that.settings.vectorize.map_vector_field = "w2v_vector"
      that.settings.rendering.size.type = "score"
      that.settings.rendering.size.parameter = ""
      that.available_vector_fields = []
      that.available_number_fields = []
      that.available_language_filters = []
      that.available_ranking_options = []
      that.settings.search.result_language = "en"
      that.settings.search.ranking_settings = {}

      const all_default_search_fields = Object.values(this.datasets)
        .filter(dataset => this.settings.search.dataset_ids.includes(dataset.id))
        .map(dataset => dataset.schema.default_search_fields)
        .reduce((acc, fields) => acc.concat(fields), []);

      for (const dataset_id of this.settings.search.dataset_ids) {
        const dataset = this.datasets[dataset_id]

        // initialize available search fields:
        for (const field of Object.values(dataset.schema.object_fields)) {
          if (field.is_available_for_search) {
            that.settings.search.separate_queries[field.identifier] = {
              query: "",
              query_negative: "",
              must: false,
              threshold_offset: 0.0,
              use_for_combined_search: all_default_search_fields.includes(
                field.identifier
              ),
            }
          }
        }

        // initialize available number and vector fields:
        for (const field of Object.values(dataset.schema.object_fields)) {
          if (field.field_type == FieldType.VECTOR) {
            that.available_vector_fields.push([dataset.id, field.identifier])
          } else if (
            field.field_type == FieldType.INTEGER ||
            field.field_type == FieldType.FLOAT
          ) {
            that.available_number_fields.push([dataset.id, field.identifier])
          }
        }

        if (dataset.merged_advanced_options.language_filtering?.options) {
          for (const language of dataset.merged_advanced_options.language_filtering.options) {
            that.available_language_filters.push([dataset.id, language])
          }
        }
        if (dataset.merged_advanced_options.default_result_language) {
          // FIXME: this is not called for new workflow with collections as the core
          that.settings.search.result_language = dataset.merged_advanced_options.default_result_language
        }
      }

      // ranking options are only supported if there is only one dataset selected:
      if (this.settings.search.dataset_ids.length == 1) {
        const dataset = this.datasets[this.settings.search.dataset_ids[0]]
        if (dataset.merged_advanced_options.ranking_options?.length > 0) {
          that.available_ranking_options = dataset.merged_advanced_options.ranking_options
          that.settings.search.ranking_settings = dataset.merged_advanced_options.ranking_options[0]
        }
      }

      // select best map vector field:
      const default_map_fields = this.settings.search.dataset_ids.map(dataset_id => this.datasets[dataset_id].merged_advanced_options.map_vector_field)
      // if all datasets have the same default map vector field, use it:
      if (default_map_fields.every((field) => field == default_map_fields[0]) && default_map_fields[0] != undefined) {
        that.settings.vectorize.map_vector_field = default_map_fields[0]
        //console.log(`all datasets have the same default map vector field, use it (${that.settings.vectorize.map_vector_field})`)
      } else {
        // check if one of the default fields is also available as a non-default field of all others:
        for (const field of default_map_fields) {
          let all_datasets_have_field = true
          for (const dataset_id of this.settings.search.dataset_ids) {
            if (!this.datasets[dataset_id].schema.object_fields[field]) {
              all_datasets_have_field = false
              break
            }
          }
          if (all_datasets_have_field) {
            that.settings.vectorize.map_vector_field = field
            //console.log(`all datasets have the same default map vector field, use it (${that.settings.vectorize.map_vector_field})`)
            break
          }
        }
      }

      // select best size field:
      const default_size_fields = this.settings.search.dataset_ids.map(dataset_id => this.datasets[dataset_id].merged_advanced_options.size_field)
      // if all datasets have the same default size field, use it:
      if (default_size_fields.every((field) => field == default_size_fields[0]) && default_size_fields[0] != undefined) {
        that.settings.rendering.size.type = "number_field"
        that.settings.rendering.size.parameter = default_size_fields[0]
        //console.log(`all datasets have the same default size field, use it (${that.settings.rendering.size.parameter})`)
      } else {
        // check if one of the default fields is also available as a non-default field of all others:
        for (const field of default_size_fields) {
          let all_datasets_have_field = true
          for (const dataset_id of this.settings.search.dataset_ids) {
            if (!this.datasets[dataset_id].schema.object_fields[field]) {
              all_datasets_have_field = false
              break
            }
          }
          if (all_datasets_have_field) {
            that.settings.rendering.size.type = "number_field"
            that.settings.rendering.size.parameter = field
            //console.log(`all datasets have the same default size field, use it (${that.settings.rendering.size.parameter})`)
            break
          }
        }
      }

    },
    reset_search_results_and_map(params = { leave_map_unchanged: false }) {
      // results:
      this.is_loading_search_results = false
      this.search_result_ids = []
      this.search_result_total_matches = 0
      this.search_result_items = {}
      this.map_id = null
      this.map_item_details = []
      this.cluster_data = []
      this.clusterIdsPerPoint = []
      this.highlighted_item_id = null
      this.highlighted_cluster_id = null
      this.selected_cluster_id = null
      this.mapState.visited_point_indexes = []
      this.mapState.map_parameters = null
      this.mapState.answer = null

      this.search_result_score_info = null
      if (this.score_info_chart) this.score_info_chart.destroy()
      this.score_info_chart = null
      this.map_timings = []
      this.search_timings = []

      // mapping progress:
      this.map_is_in_progess = false
      this.extended_search_results_are_loading = false
      this.map_viewport_is_adjusted = false
      this.show_loading_bar = false
      this.map_viewport_is_adjusted = false
      this.progress = 0.0
      this.progress_step_title = ""
      this.fields_already_received = new Set()
      this.last_position_update_received = null

      // map:
      if (!params.leave_map_unchanged) {
        this.eventBus.emit("reset_map")
      }
      // always remove cluster labels before new map is loaded:
      this.mapState.clusterData = []

      // selection:
      this.selected_document_ds_and_id = null
      this.selected_document_relevant_parts = []
      this.selected_document_query = ""
      this.selected_document_initial_item = null
      this.document_details_dialog_is_visible = false
      this.mapState.reset_visibility_filters()

      this.eventBus.emit("search_results_cleared")
    },
    reset_search_box() {
      // TODO: maybe rather restore using default settings?
      this.settings.search.task_type = null
      this.settings.search.search_type = "external_input"
      this.settings.search.use_separate_queries = false
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = ""
      this.settings.search.origins = []
      this.settings.search.filters = []
      this.settings.search.question = ""
      this.settings.search.result_language = "en"
      this.settings.search.ranking_settings = {}

      this.settings.search.cluster_origin_map_id = null
      this.settings.search.cluster_id = null
      this.settings.search.collection_id_and_class = null
      this.settings.search.similar_to_item_id = null

      this.settings.projection = JSON.parse(
        JSON.stringify(this.default_settings.projection)
      )
      this.settings.rendering = JSON.parse(
        JSON.stringify(this.default_settings.rendering)
      )

      const emptyQueryParams = new URLSearchParams()
      emptyQueryParams.set("organization_id", this.organization_id)
      emptyQueryParams.set("dataset_ids", this.settings.search.dataset_ids.join(","))
      history.pushState(null, null, "?" + emptyQueryParams.toString())
    },
    open_search_edit_mode() {
      const map_settings = JSON.parse(JSON.stringify(this.mapState.map_parameters))
      this.reset_search_results_and_map()
      const frontend_settings = JSON.parse(JSON.stringify(this.default_settings.frontend))
      map_settings.frontend = frontend_settings
      this.settings = map_settings
      // wait till Search Task Creation Dialog is loaded:
      setTimeout(() => {
        this.eventBus.emit('edit_search_parameters')
      }, 100)
    },
    run_search_from_history(history_item) {
      this.settings = JSON.parse(JSON.stringify(history_item.parameters))
      this.request_search_results()
    },
    check_if_search_is_allowed(params = {use_credit: false}) {
      // check if the user has searched something before and is not logged in
      if (!this.logged_in && document.cookie.includes("searched_without_login=true")) {
        this.eventBus.emit("show_login_dialog", {message: "Login or register to continue searching"})
        return false
      }

      // set a cookie to remember that the user has searched something
      if (params.use_credit && !this.logged_in) {
        // max-age is in seconds, 2592000 = 30 days
        document.cookie = "searched_without_login=true; max-age=2592000; path=/"
      }
      return true
    },
    request_search_results() {
      const that = this
      if (!this.check_if_search_is_allowed({use_credit: true})) return

      if (this.settings.search.dataset_ids.length === 0) return

      if (
        this.settings.search.search_type == "external_input" &&
        !this.settings.search.use_separate_queries &&
        !this.settings.search.all_field_query &&
        !this.settings.search.filters.length
      ) {
        this.reset_search_results_and_map()
        this.reset_search_box()
        return
      }

      this.is_loading_search_results = true

      // postprocess search query:
      if (this.settings.search.search_type == "external_input"
          && ["vector", "hybrid"].includes(this.settings.search.retrieval_mode)) {
        this.convert_quoted_parts_to_filter()
      }
      if (this.settings.search.retrieval_mode != "keyword") {
        // for now, ranking settings are not supported in vector or hybrid search:
        this.settings.search.ranking_settings = {}
      }

      // if (!this.settings.search.question) {
      //   this.settings.search.question = `Short summary of results for query '${this.settings.search.all_field_query}'`
      // }

      this.add_search_history_item()

      httpClient
        .post(
          `/data_backend/search_list_result?ignore_cache=${this.ignore_cache}`,
          this.settings
        )
        .then(function (response) {
          that.show_received_search_results(response.data)
          if (that.load_map_after_search) {
            that.request_map()
          }
        })
        .catch(function (error) {
          that.show_error_dialog = true
          that.error_dialog_message = `An error occurred: ${error.response.data}`
        })
        .finally(() => {
          this.is_loading_search_results = false
        })
    },
    convert_quoted_parts_to_filter() {
      // convert quoted phrases to filters if using meaning or hybrid search:
        // (keyword search supports it through 'simple query string' syntax)
        const negative_quoted_phrases = this.settings.search.all_field_query.match(/\-"([^"]*)"/g)
        if (negative_quoted_phrases) {
          for (const match of negative_quoted_phrases) {
            this.settings.search.all_field_query = this.settings.search.all_field_query.replace(match, "")
            const phrase = match.slice(2, -1)
            let already_exists = this.settings.search.filters.some(filter => filter.value === phrase)
            if (already_exists) continue
            this.settings.search.filters.push({
              field: "_descriptive_text_fields",
              dataset_id: this.settings.search.dataset_ids[0],
              operator: "does_not_contain",
              value: phrase,
            })
          }
        }
        const quoted_phrases = this.settings.search.all_field_query.match(/"([^"]*)"/g)
        if (quoted_phrases) {
          for (const match of quoted_phrases) {
            //this.settings.search.all_field_query = this.settings.search.all_field_query.replace(match, "")
            const phrase = match.slice(1, -1)
            let already_exists = this.settings.search.filters.some(filter => filter.value === phrase)
            if (already_exists) continue
            this.settings.search.filters.push({
              field: "_descriptive_text_fields",
              dataset_id: this.settings.search.dataset_ids[0],
              operator: "contains",
              value: phrase,
            })
          }
        }
    },
    answer_question() {
      // FIXME: outdated, replaced by create_chat_from_search_settings
      const that = this
      if (this.settings.search.dataset_ids.length === 0) return
      if (
        this.settings.search.search_type == "external_input" &&
        !this.settings.search.use_separate_queries &&
        !this.settings.search.all_field_query &&
        !this.settings.search.filters.length
      ) {
        this.reset_search_results_and_map()
        this.reset_search_box()
        return
      }

      this.reset_search_results_and_map({ leave_map_unchanged: false })
      this.eventBus.emit("map_regenerate_attribute_arrays_from_fallbacks")  // is this needed?

      this.convert_quoted_parts_to_filter()

      const body = { search_settings: this.settings.search }
      httpClient
        .post(`/org/data_map/create_chat_from_search_settings`, body)
        .then(function (response) {
          const chat_data = response.data
          that.chats.unshift(chat_data)
          that.eventBus.emit("show_chat", {chat_id: chat_data.id})
          that.reset_search_box()
        })
    },
    create_chat_from_search_settings(on_success) {
      const that = this
      if (this.settings.search.dataset_ids.length === 0) return
      if (!this.settings.search.all_field_query) return

      // TODO: needs to be checked if it removes the quoted parts (what it should in this case)
      // this.convert_quoted_parts_to_filter()

      const body = { search_settings: this.settings.search }
      httpClient
        .post(`/org/data_map/create_chat_from_search_settings`, body)
        .then(function (response) {
          const chat_data = response.data
          that.chats.unshift(chat_data)
          if (on_success) {
            on_success(chat_data)
          }
          that.eventBus.emit("show_chat", {chat_id: chat_data.id})
          that.reset_search_box()
        })
    },
    remove_chat(chat_id, on_success) {
      const that = this
      httpClient
        .post(`/org/data_map/delete_chat`, { chat_id: chat_id })
        .then(function (response) {
          if (on_success) {
            on_success()
          }
          that.chats = that.chats.filter((chat) => chat.id !== chat_id)
        })
    },
    get_current_map_name() {
      let name = ""
      let display_name = ""
      if (this.settings.search.search_type == "external_input") {
        if (this.settings.search.use_separate_queries) {
          name = "TODO: separate fields"
          display_name = name
        } else {
          name = this.settings.search.all_field_query
          if (this.settings.search.all_field_query_negative) {
            name = name + ` (-${this.settings.search.all_field_query_negative})`
          }
          if (this.settings.search.filters.length > 0) {
            const filter_part = this.settings.search.filters.length > 1 ? ` (${this.settings.search.filters.length} filters)` : ` (${this.settings.search.filters.length} filter)`
            name = name + filter_part
          }
          display_name = name
        }
      } else if (this.settings.search.search_type == "cluster") {
        name = `Cluster '${this.settings.search.cluster_id}'`
        display_name = `<i>Cluster</i> '${this.settings.search.origin_display_name}'`
      } else if (this.settings.search.search_type == "map_subset") {
        name = `Custom Selection`
        display_name = `Custom Selection`
      } else if (this.settings.search.search_type == "similar_to_item") {
        name = `Similar to '${this.settings.search.origin_display_name}'`
        display_name = `<i>Similar to</i> '${this.settings.search.origin_display_name}'`
      } else if (this.settings.search.search_type == "collection") {
        name = `Collection '${this.settings.search.origin_display_name}'`
        display_name = `<i>Collection</i> '${this.settings.search.origin_display_name}'`
      } else if (
        this.settings.search.search_type == "recommended_for_collection"
      ) {
        name = `Recommended for collection '${this.settings.search.origin_display_name}'`
        display_name = `<i>Recommended for collection</i> '${this.settings.search.origin_display_name}'`
      } else if (this.settings.search.search_type == "global_map") {
        name = `Overview`
        display_name = `Overview`
      }
      return [name, display_name]
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

      const [name, display_name] = this.get_current_map_name()
      if (!name) return

      const history_item_body = {
        organization_id: this.organization_id,
        name: name,
        display_name: display_name,
        parameters: this.settings,
      }

      httpClient
        .post("/org/data_map/add_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history.push(response.data)
        })

      umami.track("search", { name: name })
    },
    update_search_history_item() {
      const that = this
      if (!this.store_search_history) return

      // TODO: check if map_settings are actully the ones in the last history item

      const history_item_body = {
        item_id: this.search_history[this.search_history.length - 1].id,
        total_matches: this.search_result_total_matches,
        auto_relaxed: null,  // TODO: implement
        cluster_count: this.mapState.clusterData.length,
        result_information: {
          shown_results: this.search_result_ids.length,
        },
      }

      httpClient
        .post("/org/data_map/update_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history[that.search_history.length - 1] = response.data
        })
    },
    show_received_search_results(response_data) {
      this.reset_search_results_and_map({ leave_map_unchanged: true })
      this.eventBus.emit("map_regenerate_attribute_arrays_from_fallbacks")
      this.eventBus.emit("show_results_tab")
      this.selected_app_tab = "explore"

      this.search_result_ids = response_data["sorted_ids"]
      this.search_result_total_matches = response_data["total_matches"]
      this.search_result_items = response_data["items_by_dataset"]
      this.search_timings = response_data["timings"]
    },
    // -------- Visibility Filters & Lasso Selection (see mapStateStore for more) --------
    update_visible_result_ids() {
      this.visible_result_ids = this.search_result_ids
        .filter(
          (item_ds_and_id, i) => {
            let visible = this.selected_cluster_id == null ||
              this.clusterIdsPerPoint[i] == this.selected_cluster_id
            const item = this.search_result_items[item_ds_and_id[0]][item_ds_and_id[1]]
            visible = visible && this.mapState.visibility_filters.every(
              (filter_item) => filter_item.filter_fn(item)
            )
            return visible
          }
        )
      this.eventBus.emit("visible_result_ids_updated")
    },
    // ------------------------------------------------------
    request_map() {
      const that = this
      if (this.settings.search.dataset_ids.length === 0) return

      that.extended_search_results_are_loading = true
      that.show_loading_bar = true
      that.progress_step_title = "Requesting map..."
      that.progress = 0.0

      httpClient
        .post(
          `/data_backend/map?ignore_cache=${this.ignore_cache}`,
          this.settings
        )
        .then(function (response) {
          that.map_id = response.data["map_id"]
          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.progress = 0.1
          that.request_mapping_progress()
        })
        .catch(function (error) {
          console.log(error)
          that.extended_search_results_are_loading = false
          that.show_loading_bar = false
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
        "raw_projections",
        "scores",
        "last_parameters",
      ]
      if (!that.debug_autocut) {
        not_needed.push("search_result_score_info")
      }

      const payload = {
        map_id: this.map_id,
        exclude_fields: not_needed.concat(Array.from(this.fields_already_received)),
        last_position_update_received: this.last_position_update_received,
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
            that.extended_search_results_are_loading = false
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
        content_type == "application/cbor" ? cborDecode(new Uint8Array(response.data)) : response.data
      that.map_data = data

      if (data["finished"]) {
        // no need to get further results:
        that.map_is_in_progess = false
        that.extended_search_results_are_loading = false
      }

      if (data["errors"] && data["errors"].length > 0) {
        this.show_error_dialog = true
        this.error_dialog_message = `An error occurred: ${data["errors"].join(", ")}`
        this.reset_search_results_and_map()
        return
      }

      if (data["parameters"]) {
        that.mapState.map_parameters = data["parameters"]
        that.fields_already_received.add("parameters")
      }

      const progress = data["progress"]

      that.show_loading_bar = !progress.embeddings_available
      that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
      that.progress_step_title = progress.step_title

      const results = data["results"]
      if (results) {
        if (results["slimmed_items_per_dataset"] && Object.keys(results["slimmed_items_per_dataset"]).length > 0) {
          that.map_item_details = results["slimmed_items_per_dataset"]
          that.mapState.text_data = results["slimmed_items_per_dataset"]
          that.search_result_items = results["slimmed_items_per_dataset"]
          that.fields_already_received.add("slimmed_items_per_dataset")
        }

        const results_per_point = results["per_point_data"]
        if (results_per_point["item_ids"]?.length > 0) {
          that.search_result_ids = results_per_point["item_ids"]
          this.search_result_total_matches = results["total_matches"]
          that.mapState.per_point.item_id = results_per_point["item_ids"]
          that.fields_already_received.add("item_ids")
          that.extended_search_results_are_loading = false
        }

        // TODO: restore good gamma corrections:
        // that.mapState.per_point.size = normalizeArrayMedianGamma(results_per_point["size"], 2.0)
        // that.mapState.saturation = normalizeArrayMedianGamma(results_per_point["sat"], 3.0, 0.001)

        let should_update_geometry = false
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
            const is_hue_attr = ["hue", "secondary_hue"].includes(attr)
            const is_integer_attr_type = ["cluster_idx", "origin_query_idx"].includes(attr_params.type)
            const is_integer_field = attr_params.type == "number_field" && that.datasets[that.mapState.map_parameters?.search.dataset_ids[0]].schema.object_fields[attr_params.parameter]?.field_type == FieldType.INTEGER
            if (is_hue_attr && (is_integer_attr_type || is_integer_field)) {
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
                2.0,
                0.0001
              )
            }
            that.fields_already_received.add(attr)
            should_update_geometry = true
          }
        }

        if (results_per_point["cluster_ids"]?.length > 0) {
          that.mapState.per_point.cluster_id = results_per_point["cluster_ids"]
          that.clusterIdsPerPoint = results_per_point["cluster_ids"]
          that.fields_already_received.add("cluster_ids")
        } else if (!that.fields_already_received.has("cluster_ids")) {
          that.mapState.per_point.cluster_id = Array(
            that.mapState.per_point.x.length
          ).fill(-1)
        }

        if (results_per_point["positions_x"]?.length > 0) {
          that.mapState.per_point.x = results_per_point["positions_x"]
          should_update_geometry = true
          that.last_position_update_received = results["last_position_update"]
        }
        if (results_per_point["positions_y"]?.length > 0) {
          that.mapState.per_point.y = results_per_point["positions_y"]
          should_update_geometry = true
          that.last_position_update_received = results["last_position_update"]
        }
        if (should_update_geometry) {
          that.eventBus.emit("map_update_geometry")
        }

        if (results_per_point["thumbnail_aspect_ratios"]?.length > 0) {
          that.mapState.per_point.thumbnail_aspect_ratio =
            results_per_point["thumbnail_aspect_ratios"]
          that.fields_already_received.add("thumbnail_aspect_ratios")
        }

        if (
          results["thumbnail_atlas_filename"] &&
          results["thumbnail_atlas_filename"] !== "loading"
        ) {
          console.log("thumbnail atlas received, loading...")
          const image = new Image()
          image.src =
            "data_backend/map/thumbnail_atlas/" + results["thumbnail_atlas_filename"]
          image.onload = () => {
            console.log("thumbnail atlas loaded", image, results["thumbnail_sprite_size"])
            that.mapState.textureAtlas = image
            that.mapState.thumbnailSpriteSize = results["thumbnail_sprite_size"]
            that.eventBus.emit("map_update_geometry")
            console.log("thumbnail atlas done")
          }
          that.fields_already_received.add("thumbnail_atlas_filename")
          //that.settings.frontend.rendering.point_size_factor = 3.0
          //that.settings.frontend.rendering.max_opacity = 1.0
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

        if (results["answer"]) {
          that.mapState.answer = results["answer"]
          that.fields_already_received.add("answer")
        }

        that.map_timings = results["timings"]

        if (!that.map_is_in_progess) {
          that.update_search_history_item()
        }
      }
    },
    cluster_selected(cluster_item) {
      this.narrow_down_on_cluster(cluster_item)
    },
    cluster_hovered(cluster_id) {
      this.highlighted_cluster_id = cluster_id
    },
    cluster_hover_end(cluster_id) {
      this.highlighted_cluster_id = null
    },
    get_current_origin() {
      const current_map_name = this.get_current_map_name()
      const origin = {
        type: this.mapState.map_parameters.search.search_type,
        name: current_map_name[0],
        display_name: current_map_name[1],
        map_id: this.map_id,
      }
      return origin
    },
    narrow_down_on_cluster(cluster_item) {
      this.settings.search.origins = (this.mapState.map_parameters.search.origins || []).concat([this.get_current_origin()])
      this.settings.search.search_type = "cluster"
      this.settings.search.cluster_origin_map_id = this.map_id
      this.settings.search.cluster_id = cluster_item.id
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = cluster_item.title
      this.set_two_dimensional_projection()
      this.request_search_results()
    },
    narrow_down_on_selection(selected_items) {
      this.settings.search.origins = (this.mapState.map_parameters.search.origins || []).concat([this.get_current_origin()])
      this.settings.search.search_type = "map_subset"
      this.settings.search.cluster_origin_map_id = this.map_id
      this.settings.search.selected_items = selected_items
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = "Custom Selection"
      this.set_two_dimensional_projection()
      this.mapState.visibility_filters = []
      this.eventBus.emit("visibility_filters_updated")
      this.request_search_results()
    },
    show_collection_as_map(collection, class_name) {
      this.settings.search.search_type = "collection"
      this.settings.search.collection_id_and_class = [collection.id, class_name]
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = `${collection.name}: ${class_name}`
      this.settings.search.origins = []
      this.set_two_dimensional_projection()
      this.request_search_results()
    },
    recommend_items_for_collection(collection, class_name) {
      this.settings.search.search_type = "recommended_for_collection"
      this.settings.search.collection_id_and_class = [collection.id, class_name]
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origin_display_name = `${collection.name}: ${class_name}`
      this.settings.search.origins = []
      this.request_search_results()
    },
    show_global_map(dataset_ids = []) {
      if (dataset_ids.length > 0) {
        this.settings.search.dataset_ids = dataset_ids
        this.on_selected_datasets_changed()
      }
      this.settings.search.search_type = "global_map"
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      this.settings.search.origins = []
      this.settings.search.filters = []
      this.set_two_dimensional_projection()
      this.request_search_results()
    },
    show_document_details(dataset_and_item_id, initial_item=null, relevant_parts=null, query=null) {
      this.selected_document_relevant_parts = relevant_parts || []
      this.selected_document_query = query || ""
      this.selected_document_ds_and_id = dataset_and_item_id
      this.selected_document_initial_item = initial_item || this.get_item_by_ds_and_id(dataset_and_item_id)
      const pointIdx = this.mapState.per_point.item_id.indexOf(dataset_and_item_id)
      this.document_details_dialog_is_visible = true
      if (pointIdx !== -1) {
        this.mapState.markedPointIdx = pointIdx
        this.mapState.visited_point_indexes.push(pointIdx)
        this.mapState.per_point.flatness[pointIdx] = 1.0
        this.eventBus.emit("map_update_geometry")
      }
    },
    close_document_details() {
      this.document_details_dialog_is_visible = false
      this.selected_document_ds_and_id = null
      this.selected_document_relevant_parts = []
      this.selected_document_query = ""
      this.selected_document_initial_item = null
      this.mapState.markedPointIdx = -1
    },
    set_polar_projection() {
      this.settings.projection.use_polar_coordinates = true
      this.settings.projection.x_axis = { type: "score", parameter: "" }
      this.settings.projection.y_axis = {
        type: "embedding",
        parameter: "primary",
      }
    },
    set_two_dimensional_projection() {
      this.settings.projection.use_polar_coordinates = false
      this.settings.projection.x_axis = {
        type: "embedding",
        parameter: "primary",
      }
      this.settings.projection.y_axis = {
        type: "embedding",
        parameter: "primary",
      }
    },
    show_similar_items(item_ds_and_id, full_item=null) {
      this.settings.search.search_type = "similar_to_item"
      this.settings.search.similar_to_item_id = item_ds_and_id
      this.settings.search.retrieval_mode = "vector"
      // use currently selected datasets, no need to change them
      this.settings.search.all_field_query = ""
      this.settings.search.all_field_query_negative = ""
      const title_func = this.datasets[item_ds_and_id[0]].schema.hover_label_rendering.title
      if (!full_item) {
        const ds_items = this.map_item_details[item_ds_and_id[0]]
        full_item = ds_items ? ds_items[item_ds_and_id[1]] : null
      }
      this.settings.search.origin_display_name = full_item ? title_func(full_item) : "Seed Item"
      this.set_polar_projection()
      // keep the map, but indexes will change, so reset them:
      this.mapState.markedPointIdx = -1
      this.request_search_results()
    },
    get_item_by_ds_and_id(dataset_and_item_id) {
      const ds_items = this.map_item_details[dataset_and_item_id[0]]
      const item = ds_items ? ds_items[dataset_and_item_id[1]] : null
      return item || {_dataset_id: dataset_and_item_id[0], _id: dataset_and_item_id[1]}
    },
    get_dataset_by_index(item_index) {
      if (!this.mapState.per_point.item_id[item_index]) return undefined
      const [dataset_id, item_id] = this.mapState.per_point.item_id[item_index]
      return this.datasets[dataset_id]
    },
    get_hover_rendering_by_index(item_index) {
      return this.get_dataset_by_index(item_index)?.schema.hover_label_rendering
    },
    store_current_map() {
      const that = this
      const [name, display_name] = this.get_current_map_name()
      if (!name) return
      const store_map_body = {
        user_id: this.user.id,
        organization_id: this.organization_id,
        name: name,
        display_name: display_name,
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

      this.reset_search_results_and_map()
      this.eventBus.emit("show_results_tab")

      that.map_id = stored_map_id
      const body = {
        map_id: this.map_id,
      }

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
          that.extended_search_results_are_loading = true
          that.request_mapping_progress()
        })
        .catch(function (error) {
          if (error.response && error.response.status === 404) {
            // map doesn't exist anymore, go back to clear page and reset URL parameters:
            that.show_error_dialog = true
            that.error_dialog_message = `The requested map doesn't exist anymore.`
            that.reset_search_box()
          }
        })
    },
    add_selected_points_to_collection(collection_id, class_name, is_positive) {
      // TODO: implement more efficient way
      for (const ds_and_item_id of this.visible_result_ids) {
        this.collectionStore.add_item_to_collection(ds_and_item_id, collection_id, class_name, is_positive, false)
      }
      this.toast.add({severity: 'success', summary: 'Items added to collection', detail: `${this.visible_result_ids.length} items added to the collection`, life: 3000})
    },
    remove_selected_points_from_collection(collection_id, class_name) {
      // TODO: implement more efficient way
      for (const ds_and_item_id of this.visible_result_ids) {
        this.collectionStore.remove_item_from_collection(ds_and_item_id, collection_id, class_name, false)
      }
      this.toast.add({severity: 'success', summary: 'Items removed from collection', detail: `${this.visible_result_ids.length} items removed from the collection`, life: 3000})
    },
  },
})
