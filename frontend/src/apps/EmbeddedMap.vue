<script setup>
import cborJs from "https://cdn.jsdelivr.net/npm/cbor-js@0.1.0/+esm"

import { mapStores } from "pinia"

import { Chart } from "chart.js/auto"
import annotationPlugin from "chartjs-plugin-annotation"

import InteractiveMap from "../components/map/InteractiveMap.vue"
import SearchArea from "../components/search/SearchArea.vue"
import ResultListItem from "../components/search/ResultListItem.vue"
import ObjectDetailsModal from "../components/search/ObjectDetailsModal.vue"
import Classifier from "../components/classifier/Classifier.vue"
import ClassifierExample from "../components/classifier/ClassifierExample.vue"

import httpClient from "../api/httpClient"
import { FieldType, normalizeArray, normalizeArrayMedianGamma } from "../utils/utils"
import { useAppStateStore } from "../stores/settings_store"

const appState = useAppStateStore()

Chart.register(annotationPlugin)
</script>

<script>
export default {
  data() {
    return {
      // results:
      search_results: [],
      result_list_rendering: {},
      map_id: null,
      map_item_details: [],
      cluster_data: [],
      clusterIdsPerPoint: [],

      search_result_score_info: null,
      score_info_chart: null,
      search_timings: "",
      map_timings: "",

      search_history: [],

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

      // tabs:
      selected_tab: "map",

      // classifiers:
      last_used_classifier_id: null,

      // stored maps:
      stored_maps: [],
    }
  },
  methods: {
    reset_search_results_and_map(params = { leave_map_unchanged: false }) {
      // results:
      this.search_results = []
      this.map_task_id = null
      this.map_item_details = []
      this.cluster_data = []
      this.clusterIdsPerPoint = []
      this.appStateStore.highlighted_item_id = null
      this.appStateStore.selected_item_id = null
      this.appStateStore.highlighted_cluster_id = null
      this.appStateStore.selected_cluster_id = null

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
        this.$refs.embedding_map.resetData()
        this.$refs.embedding_map.resetPanAndZoom()
      }

      // selection:
      this.selectedDocumentIdx = -1
      this.selectedDocumentDetails = null
    },
    reset_search_box() {
      this.appStateStore.settings.search.search_type = "external_input"
      this.appStateStore.settings.search.use_separate_queries = false
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = ""

      this.appStateStore.settings.search.cluster_origin_map_id = null
      this.appStateStore.settings.search.cluster_id = null
      this.appStateStore.settings.search.classifier_id = null
      this.appStateStore.settings.search.similar_to_item_id = null

      this.appStateStore.settings.projection = JSON.parse(
        JSON.stringify(this.appStateStore.default_settings.projection)
      )
      this.appStateStore.settings.rendering = JSON.parse(
        JSON.stringify(this.appStateStore.default_settings.rendering)
      )
    },
    run_search_from_history(history_item) {
      this.appStateStore.settings = history_item.parameters
      this.request_search_results()
    },
    request_search_results() {
      const that = this

      if (
        this.appStateStore.settings.search.search_type == "external_input" &&
        !this.appStateStore.settings.search.use_separate_queries &&
        !this.appStateStore.settings.search.all_field_query
      ) {
        this.reset_search_results_and_map()
        return
      }

      this.reset_search_results_and_map({ leave_map_unchanged: true })
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
      ]) {
        that.$refs.embedding_map.attribute_fallback[attr] =
          that.appStateStore.settings.frontend.rendering[attr].fallback
      }
      that.$refs.embedding_map.regenerateAttributeArraysFromFallbacks()
      this.selected_tab = "results"

      this.add_search_history_item()

      httpClient
        .post(
          `/data_backend/search_list_result?ignore_cache=${this.appStateStore.ignore_cache}`,
          this.appStateStore.settings
        )
        .then(function (response) {
          that.show_received_search_results(response.data)
          that.request_map()
        })
    },
    show_received_search_results(response_data) {
      this.search_results = response_data["items"]
      this.search_timings = response_data["timings"]
    },
    get_current_map_name() {
      let entry_name = ""
      if (this.appStateStore.settings.search.search_type == "external_input") {
        if (this.appStateStore.settings.search.use_separate_queries) {
          entry_name = "TODO: separate fields"
        } else {
          entry_name = this.appStateStore.settings.search.all_field_query
          if (this.appStateStore.settings.search.all_field_query_negative) {
            entry_name =
              entry_name + ` (-${this.appStateStore.settings.search.all_field_query_negative})`
          }
        }
      } else if (this.appStateStore.settings.search.search_type == "cluster") {
        entry_name = `<i>Cluster</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (this.appStateStore.settings.search.search_type == "similar_to_item") {
        entry_name = `<i>Similar to</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (this.appStateStore.settings.search.search_type == "classifier") {
        entry_name = `<i>Classifier</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (
        this.appStateStore.settings.search.search_type == "recommended_for_classifier"
      ) {
        entry_name = `<i>Recommended for classifier</i> '${this.appStateStore.settings.search.origin_display_name}'`
      }
      return entry_name
    },
    add_search_history_item() {
      const that = this
      if (!this.appStateStore.store_search_history) return

      if (
        this.search_history.length > 0 &&
        JSON.stringify(this.search_history[this.search_history.length - 1].parameters) ==
          JSON.stringify(this.appStateStore.settings)
      ) {
        // -> same query as before, don't save this duplicate:
        return
      }

      const entry_name = this.get_current_map_name()
      if (!entry_name) return

      const history_item_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
        name: entry_name,
        parameters: this.appStateStore.settings,
      }

      httpClient
        .post("/org/data_map/add_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history.push(response.data)
        })
    },
    request_map() {
      const that = this

      httpClient
        .post(
          `/data_backend/map?ignore_cache=${this.appStateStore.ignore_cache}`,
          this.appStateStore.settings
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
      if (!that.appStateStore.debug_autocut) {
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
          const content_type = response.headers["content-type"]
          const data =
            content_type == "application/cbor" ? cborJs.decode(response.data) : response.data

          if (data["finished"]) {
            // no need to get further results:
            that.map_is_in_progess = false
          }

          const progress = data["progress"]

          that.show_loading_bar = !progress.embeddings_available
          that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
          that.progress_step_title = progress.step_title

          if (that.appStateStore.dataset.thumbnail_image) {
            that.$refs.embedding_map.pointSizeFactor = 3.0
            that.$refs.embedding_map.maxOpacity = 1.0
          } else {
            that.$refs.embedding_map.pointSizeFactor = 1.0
            that.$refs.embedding_map.maxOpacity = 0.7
          }

          const results = data["results"]
          if (results) {
            const results_per_point = results["per_point_data"]
            if (
              results_per_point["hover_label_data"] &&
              results_per_point["hover_label_data"].length > 0
            ) {
              that.map_item_details = results_per_point["hover_label_data"]
              that.$refs.embedding_map.per_point.text_data =
                results_per_point["hover_label_data"]
              that.search_results = results_per_point["hover_label_data"]
              that.fields_already_received.add("hover_label_data")
            }

            // TODO: restore good gamma corrections:
            // that.$refs.embedding_map.per_point.size = normalizeArrayMedianGamma(results_per_point["size"], 2.0)
            // that.$refs.embedding_map.saturation = normalizeArrayMedianGamma(results_per_point["sat"], 3.0, 0.001)

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
            ]) {
              if (results_per_point[attr] && results_per_point[attr].length > 0) {
                const attr_params = that.appStateStore.settings.rendering[attr]
                if (
                  ["hue", "secondary_hue"].includes(attr) &&
                  (["cluster_idx", "origin_query_idx"].includes(attr_params.type) ||
                    (attr_params.type == "number_field" &&
                      that.appStateStore.dataset.object_fields[attr_params.parameter]
                        .field_type == FieldType.INTEGER))
                ) {
                  // if an integer value is assigned to a hue value, we need to make sure that the last value doesn't have
                  // the same hue as the first value:
                  results_per_point[attr].push(Math.max(...results_per_point[attr]) + 1)
                  that.$refs.embedding_map.per_point[attr] = normalizeArrayMedianGamma(
                    results_per_point[attr],
                    2.0
                  ).slice(0, results_per_point[attr].length - 1)
                } else {
                  that.$refs.embedding_map.per_point[attr] = normalizeArrayMedianGamma(
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
              that.$refs.embedding_map.per_point.cluster_id = results_per_point["cluster_ids"]
              that.clusterIdsPerPoint = results_per_point["cluster_ids"]
              that.fields_already_received.add("cluster_ids")
            } else if (!that.fields_already_received.has("cluster_ids")) {
              that.$refs.embedding_map.per_point.cluster_id = Array(
                that.$refs.embedding_map.per_point.x.length
              ).fill(-1)
            }

            let should_update_geometry = false
            if (
              results_per_point["positions_x"] &&
              results_per_point["positions_x"].length > 0
            ) {
              that.$refs.embedding_map.per_point.x = results_per_point["positions_x"]
              should_update_geometry = true
            }
            if (
              results_per_point["positions_y"] &&
              results_per_point["positions_y"].length > 0
            ) {
              that.$refs.embedding_map.per_point.y = results_per_point["positions_y"]
              should_update_geometry = true
            }
            if (should_update_geometry) {
              that.$refs.embedding_map.updateGeometry()
            }

            if (
              results["thumbnail_atlas_filename"] &&
              results["thumbnail_atlas_filename"] !== "loading"
            ) {
              const image = new Image()
              image.src =
                "data_backend/map/thumbnail_atlas/" + results["thumbnail_atlas_filename"]
              image.onload = () => {
                that.$refs.embedding_map.textureAtlas = image
                that.$refs.embedding_map.thumbnailSpriteSize = results["thumbnail_sprite_size"]
                that.$refs.embedding_map.updateGeometry()
              }
              that.fields_already_received.add("thumbnail_atlas_filename")
            } else if (
              results["thumbnail_atlas_filename"] &&
              results["thumbnail_atlas_filename"] === "loading"
            ) {
              that.$refs.embedding_map.textureAtlas = null
            }

            if (results["clusters"] && Object.keys(results["clusters"]).length > 0) {
              that.$refs.embedding_map.clusterData = results["clusters"]
              that.cluster_data = results["clusters"]
              that.fields_already_received.add("clusters")
            }

            if (that.map_viewport_is_adjusted) {
              that.$refs.embedding_map.centerAndFitDataToActiveAreaSmooth()
            } else {
              that.$refs.embedding_map.resetPanAndZoom()
              that.$refs.embedding_map.centerAndFitDataToActiveAreaInstant()
              that.map_viewport_is_adjusted = true
            }

            if (results["search_result_score_info"]) {
              that.search_result_score_info = results["search_result_score_info"]
              that.fields_already_received.add("search_result_score_info")
              that.show_score_info_chart()
            }

            that.map_timings = results["timings"]
          }
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
    narrow_down_on_cluster(cluster_item) {
      this.appStateStore.settings.search.search_type = "cluster"
      this.appStateStore.settings.search.cluster_origin_map_id = this.map_id
      this.appStateStore.settings.search.cluster_id = cluster_item.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = cluster_item.title
      this.request_search_results()
    },
    show_classifier_as_map(classifier) {
      this.appStateStore.settings.search.search_type = "classifier"
      this.appStateStore.settings.search.classifier_id = classifier.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = classifier.name
      this.request_search_results()
    },
    recommend_items_for_classifier(classifier) {
      this.appStateStore.settings.search.search_type = "recommended_for_classifier"
      this.appStateStore.settings.search.classifier_id = classifier.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = classifier.name
      this.request_search_results()
    },
    show_global_map() {
      this.appStateStore.settings.search.search_type = "global_map"
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.request_search_results()
    },
    show_document_details(pointIdx) {
      this.selectedDocumentIdx = pointIdx
      this.$refs.embedding_map.markedPointIdx = pointIdx
    },
    show_document_details_by_id(item_id) {
      for (const i of Array(this.map_item_details.length).keys()) {
        if (this.map_item_details[i]._id == item_id) {
          this.selectedDocumentIdx = i
          this.$refs.embedding_map.markedPointIdx = i
          break
        }
      }
    },
    showSimilarItems() {
      this.appStateStore.settings.search.search_type = "similar_to_item"
      this.appStateStore.settings.search.similar_to_item_id =
        this.map_item_details[this.selectedDocumentIdx]._id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.projection.use_polar_coordinates = true
      this.appStateStore.settings.projection.x_axis = { type: "score", parameter: "" }
      this.appStateStore.settings.projection.y_axis = { type: "umap", parameter: "primary" }
      const title_func = this.$refs.embedding_map.hover_label_rendering.title
      this.appStateStore.settings.search.origin_display_name = title_func(
        this.map_item_details[this.selectedDocumentIdx]
      )
      this.request_search_results()
    },
    close_document_details() {
      this.selectedDocumentIdx = -1
      this.$refs.embedding_map.markedPointIdx = -1
      this.selectedDocumentDetails = null
    },
    updateMapPassiveMargin() {
      this.$refs.embedding_map.passiveMarginsLRTB = [50, 50, 50, 50]
    },
    create_classifier(name) {
      const that = this
      const create_classifier_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
        name: name,
      }
      httpClient
        .post("/org/data_map/add_classifier", create_classifier_body)
        .then(function (response) {
          that.appStateStore.classifiers.push(response.data)
        })
    },
    delete_classifier(classifier_id) {
      const that = this
      const delete_classifier_body = {
        classifier_id: classifier_id,
      }
      httpClient
        .post("/org/data_map/delete_classifier", delete_classifier_body)
        .then(function (response) {
          let index_to_be_removed = null
          let i = 0
          for (const classifier of that.appStateStore.classifiers) {
            if (classifier.id == classifier_id) {
              index_to_be_removed = i
              break
            }
            i += 1
          }
          if (index_to_be_removed !== null) {
            that.appStateStore.classifiers.splice(index_to_be_removed, 1)
          }
        })
    },
    add_item_to_classifier(item_index, classifier_id, class_name, is_positive) {
      const that = this
      const classifier =
        this.appStateStore.classifiers[
          this.appStateStore.classifiers.findIndex((e) => e.id == classifier_id)
        ]
      if (!classifier) return

      this.last_used_classifier_id = classifier.id
      const item_id = this.map_item_details[item_index]._id
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
        .then(function (response) {
          // TODO: refresh list of examples if open
          // if (is_positive) {
          //   classifier.positive_ids.push(item_id)
          // } else {
          //   classifier.negative_ids.push(item_id)
          // }
        })
    },
    store_current_map() {
      const that = this
      const entry_name = this.get_current_map_name()
      if (!entry_name) return
      const store_map_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
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
          let index_to_be_removed = null
          let i = 0
          for (const map of that.stored_maps) {
            if (map.id == stored_map_id) {
              index_to_be_removed = i
              break
            }
            i += 1
          }
          if (index_to_be_removed !== null) {
            that.stored_maps.splice(index_to_be_removed, 1)
          }
        })
    },
    show_stored_map(stored_map_id) {
      console.log("showing stored map", stored_map_id)
      const that = this

      that.map_id = stored_map_id
      const body = {
        map_id: this.map_id,
      }
      this.reset_search_results_and_map()
      this.selected_tab = "results"

      httpClient
        .post("/data_backend/stored_map/parameters_and_search_results", body)
        .then(function (response) {
          const parameters = response.data.parameters
          that.appStateStore.settings = parameters
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
          ]) {
            that.$refs.embedding_map.attribute_fallback[attr] =
              that.appStateStore.settings.frontend.rendering[attr].fallback
          }
          that.$refs.embedding_map.regenerateAttributeArraysFromFallbacks()

          // now done when map results are received
          //that.show_received_search_results(response.data)

          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.request_mapping_progress()
        })
    },
    evaluate_url_query_parameters() {
      // this is almost the first thing that is done when the page is being loaded
      // most importantly, it initializes the dataset_id, which then triggers other stuff
      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("dataset_id") === null) {
        this.appStateStore.settings.dataset_id = 6
        const emptyQueryParams = new URLSearchParams()
        emptyQueryParams.set("dataset_id", this.appStateStore.settings.dataset_id)
        history.replaceState(null, null, "?" + emptyQueryParams.toString())
      } else if (
        queryParams.get("dataset_id") === String(this.appStateStore.settings.dataset_id)
      ) {
        // If this method was called because the user pressed the back arrow in the browser and
        // the dataset is the same, the stored_map might be different.
        // In this case, load it here:
        // (in any other case, the stored map is loaded after the dataset object is loaded)
        if (queryParams.get("map_id")) {
          this.show_stored_map(queryParams.get("map_id"))
        }
      } else {
        // there is a new dataset_id in the parameters:
        this.appStateStore.settings.dataset_id = parseInt(queryParams.get("dataset_id"))
      }
    },
    show_score_info_chart() {
      if (this.score_info_chart) this.score_info_chart.destroy()
      const datasets = []
      const annotations = []
      const colors = ["red", "green", "blue", "purple", "fuchsia", "aqua", "yellow", "navy"]
      let i = 0
      let maxElements = 1
      for (const score_info_title in this.search_result_score_info) {
        maxElements = Math.max(
          maxElements,
          this.search_result_score_info[score_info_title].scores.length
        )
        datasets.push({
          label: score_info_title,
          data: this.search_result_score_info[score_info_title].scores,
          borderWidth: 1,
          pointStyle: false,
          borderColor: colors[i],
        })
        annotations.push({
          type: "line",
          mode: "vertical",
          xMax: this.search_result_score_info[score_info_title].cutoff_index,
          xMin: this.search_result_score_info[score_info_title].cutoff_index,
          borderColor: colors[i],
          label: {
            display: false,
            content: score_info_title,
            position: {
              x: "center",
              y: "top",
            },
          },
        })
        i += 1
      }
      this.score_info_chart = new Chart(this.$refs.score_info_chart, {
        type: "line",
        data: {
          labels: [...Array(maxElements).keys()],
          datasets: datasets,
        },
        options: {
          plugins: {
            annotation: {
              annotations: annotations,
            },
          },
        },
      })
    },
    on_dataset_id_change() {
      const that = this

      that.appStateStore.dataset = null
      this.reset_search_results_and_map()

      httpClient
        .post("/org/data_map/dataset", { dataset_id: this.appStateStore.settings.dataset_id })
        .then(function (response) {
          that.appStateStore.dataset = response.data

          const result_list_rendering = that.appStateStore.dataset.result_list_rendering
          for (const field of ["title", "subtitle", "body", "image", "url"]) {
            result_list_rendering[field] = eval(result_list_rendering[field])
          }
          that.result_list_rendering = result_list_rendering

          const classifier_example_rendering =
            that.appStateStore.dataset.classifier_example_rendering
          for (const field of ["title", "subtitle", "body", "image", "url"]) {
            classifier_example_rendering[field] = eval(classifier_example_rendering[field])
          }
          that.appStateStore.classifier_example_rendering = classifier_example_rendering

          const hover_label_rendering = that.appStateStore.dataset.hover_label_rendering
          for (const field of ["title", "subtitle", "body", "image"]) {
            hover_label_rendering[field] = hover_label_rendering[field]
              ? eval(hover_label_rendering[field])
              : (item) => ""
          }
          that.$refs.embedding_map.hover_label_rendering = hover_label_rendering

          const queryParams = new URLSearchParams(window.location.search)
          if (
            queryParams.get("dataset_id") === String(that.appStateStore.settings.dataset_id) &&
            queryParams.get("map_id")
          ) {
            that.show_stored_map(queryParams.get("map_id"))
          } else if (
            queryParams.get("dataset_id") === String(that.appStateStore.settings.dataset_id) &&
            queryParams.get("query")
          ) {
            that.appStateStore.settings.search.all_field_query = queryParams.get("query")
            that.request_search_results()
          }
        })

      this.search_history = []
      const get_history_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_search_history", get_history_body)
        .then(function (response) {
          that.search_history = response.data
        })

      this.appStateStore.classifiers = []
      const get_classifiers_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_classifiers", get_classifiers_body)
        .then(function (response) {
          that.appStateStore.classifiers = response.data
        })

      this.stored_maps = []
      const get_stored_maps_body = {
        dataset_id: this.appStateStore.settings.dataset_id,
      }
      httpClient
        .post("/org/data_map/get_stored_maps", get_stored_maps_body)
        .then(function (response) {
          that.stored_maps = response.data
        })
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.evaluate_url_query_parameters()
    this.updateMapPassiveMargin()
    window.addEventListener("resize", this.updateMapPassiveMargin)
    window.addEventListener("popstate", this.evaluate_url_query_parameters)
  },
  watch: {
    "appStateStore.settings.dataset_id"() {
      this.on_dataset_id_change()
    },
  },
}
</script>

<template>
  <main class="overflow-hidden">
    <InteractiveMap
      ref="embedding_map"
      class="absolute top-0 h-screen w-screen"
      :appStateStore="appState"
      @cluster_selected="narrow_down_on_cluster"
      @point_selected="show_document_details"
      @cluster_hovered="(cluster_id) => (appState.highlighted_cluster_id = cluster_id)"
      @cluster_hover_end="appState.highlighted_cluster_id = null" />

    <div v-if="appState.show_timings" class="absolute bottom-0 right-0 text-right">
      <!-- timings -->
      <ul role="list">
        <li v-for="item in search_timings" :key="item.part" class="text-gray-300">
          {{ item.part }}: {{ item.duration.toFixed(2) }} s
        </li>
      </ul>
      <hr />
      <ul role="list">
        <li v-for="item in map_timings" :key="item.part" class="text-gray-300">
          {{ item.part }}: {{ item.duration.toFixed(2) }} s
        </li>
      </ul>
    </div>

    <!-- content area -->
    <div
      class="pointer-events-none relative mr-auto grid h-screen min-h-0 min-w-0 max-w-7xl grid-cols-1 gap-4 overflow-hidden px-3 pb-20 pt-6 md:grid-cols-2 md:pb-6 md:pt-6 xl:px-12"
      style="grid-auto-rows: minmax(auto, min-content)">
      <!-- right column (e.g. for showing box with details for selected result) -->
      <div
        ref="right_column"
        class="pointer-events-none flex flex-col overflow-hidden md:h-screen">
        <div
          v-if="selectedDocumentIdx !== -1 && map_item_details.length > selectedDocumentIdx"
          class="pointer-events-auto flex w-full flex-initial overflow-hidden">
          <ObjectDetailsModal
            :initial_item="map_item_details[selectedDocumentIdx]"
            :dataset="appState.dataset"
            :classifiers="appState.classifiers"
            :last_used_classifier_id="last_used_classifier_id"
            @addToPositives="
              (classifier_id, class_name) => {
                add_item_to_classifier(selectedDocumentIdx, classifier_id, class_name, true)
              }
            "
            @addToNegatives="
              (classifier_id, class_name) => {
                add_item_to_classifier(selectedDocumentIdx, classifier_id, class_name, false)
              }
            "
            @showSimilarItems="showSimilarItems"
            @close="close_document_details"></ObjectDetailsModal>
        </div>

        <div v-if="show_loading_bar" class="flex w-full flex-1 flex-col justify-center">
          <span class="self-center font-bold text-gray-400">{{ progress_step_title }}</span>
          <div class="mt-2 h-2.5 w-1/5 self-center rounded-full bg-gray-400/50">
            <div
              class="h-2.5 rounded-full bg-blue-400"
              :style="{ width: (progress * 100).toFixed(0) + '%' }"></div>
          </div>
        </div>

        <div
          v-if="!show_loading_bar && !search_results.length"
          class="align-center pointer-events-auto flex flex-1 flex-col justify-center">
          <div class="mb-6 flex flex-row justify-center">
            <img
              class="h-12"
              :src="appState.dataset ? appState.dataset.workspace_tool_logo_url : ''" />
          </div>
          <div
            class="mb-2 flex-none text-center font-bold text-gray-400"
            v-html="appState.dataset ? appState.dataset.workspace_tool_intro_text : ''"></div>
        </div>
      </div>
    </div>

    <div
      v-if="appState.dataset ? !appState.dataset.workspace_tool_title : true"
      class="absolute -right-3 bottom-4 rounded-xl bg-black py-1 pl-3 pr-5 font-['Lexend'] shadow-sm">
      <span class="font-bold text-white">Quiddity</span>
      <span class="font-light text-gray-200">Workspace</span>
    </div>

    <!--  -->
  </main>
</template>

<style scoped></style>
