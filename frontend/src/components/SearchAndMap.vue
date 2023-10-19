<script setup>
import { mapStores } from 'pinia'

import { Chart } from 'chart.js/auto'
import annotationPlugin from 'chartjs-plugin-annotation';

import EmbeddingMap from './EmbeddingMap.vue';
import SearchArea from './SearchArea.vue';
import ResultListItem from './ResultListItem.vue';
import ObjectDetailsModal from './ObjectDetailsModal.vue';
import Collection from './Collection.vue';
import CollectionListItem from './CollectionListItem.vue';

import httpClient from '../api/httpClient';
import { normalizeArray, normalizeArrayMedianGamma } from '../utils/utils'
import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()

Chart.register(annotationPlugin);

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
      fields_already_received: [],

      // selection:
      selectedDocumentIdx: -1,
      selectedDocumentDetails: null,

      // tabs:
      selected_tab: "map",

      // collections:
      collections: [],
      last_used_collection_id: null,

      // stored maps:
      stored_maps: [],
    }
  },
  methods: {
    reset_search_results_and_map(params={leave_map_unchanged: false}) {
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
      this.fields_already_received = []

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
      this.appStateStore.settings.search.search_type = 'external_input'
      this.appStateStore.settings.search.use_separate_queries = false
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = ""

      this.appStateStore.settings.search.cluster_origin_map_id = null
      this.appStateStore.settings.search.cluster_id = null
      this.appStateStore.settings.search.collection_id = null
      this.appStateStore.settings.search.similar_to_item_id = null

      this.appStateStore.settings.projection.shape = "2d"
    },
    run_search_from_history(history_item) {
      this.appStateStore.settings = history_item.parameters
      this.request_search_results()
    },
    request_search_results() {
      const that = this

      if (this.appStateStore.settings.search.search_type == 'external_input' &&
        !this.appStateStore.settings.search.use_separate_queries &&
        !this.appStateStore.settings.search.all_field_query) {
          this.reset_search_results_and_map()
          return
        }

      this.reset_search_results_and_map({leave_map_unchanged: true})
      this.selected_tab = "results"

      this.add_search_history_item()

      httpClient.post(`/data_backend/search_list_result?ignore_cache=${this.appStateStore.ignore_cache}`,
        this.appStateStore.settings)
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
      if (this.appStateStore.settings.search.search_type == 'external_input') {
        if (this.appStateStore.settings.search.use_separate_queries) {
          entry_name = "TODO: separate fields"
        } else {
          entry_name = this.appStateStore.settings.search.all_field_query
          if (this.appStateStore.settings.search.all_field_query_negative) {
            entry_name = entry_name + ` (-${this.appStateStore.settings.search.all_field_query_negative})`
          }
        }
      } else if (this.appStateStore.settings.search.search_type == 'cluster') {
        entry_name = `<i>Cluster</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (this.appStateStore.settings.search.search_type == 'similar_to_item') {
        entry_name = `<i>Similar to</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (this.appStateStore.settings.search.search_type == 'collection') {
        entry_name = `<i>Collection</i> '${this.appStateStore.settings.search.origin_display_name}'`
      } else if (this.appStateStore.settings.search.search_type == 'recommended_for_collection') {
        entry_name = `<i>Recommended for collection</i> '${this.appStateStore.settings.search.origin_display_name}'`
      }
      return entry_name
    },
    add_search_history_item() {
      const that = this
      if (!this.appStateStore.store_search_history) return;

      if (this.search_history.length > 0 &&
        JSON.stringify(this.search_history[this.search_history.length - 1].parameters)
        == JSON.stringify(this.appStateStore.settings)) {
        // -> same query as before, don't save this duplicate:
        return;
      }

      const entry_name = this.get_current_map_name()
      if (!entry_name) return;

      const history_item_body = {
        user_id: 1,  // FIXME: this is hardcoded
        schema_id: this.appStateStore.settings.schema_id,
        name: entry_name,
        parameters: this.appStateStore.settings,
      }

      httpClient.post("/organization_backend/add_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history.push(response.data)
        })
    },
    request_map() {
      const that = this

      httpClient.post(`/data_backend/map?ignore_cache=${this.appStateStore.ignore_cache}`,
        this.appStateStore.settings)
        .then(function (response) {
          that.map_id = response.data["map_id"]
          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.request_mapping_progress()
        })
    },
    request_mapping_progress() {
      const that = this

      if (!this.map_id || !this.map_is_in_progess) return;

      const queryParams = new URLSearchParams(window.location.search);
      if (queryParams.get("map_id") != this.map_id) {
        queryParams.set("map_id", this.map_id);
        history.pushState(null, null, "?"+queryParams.toString());
      }

      // note: these may be needed in the future, pay attention to remove them in this case here
      const not_needed = ['item_ids', 'raw_projections', 'search_result_meta_information', 'parameters']
      if (!that.appStateStore.debug_autocut) {
        not_needed.push("search_result_score_info")
      }

      const payload = {
        map_id: this.map_id,
        exclude_fields: not_needed + this.fields_already_received,
      }
      httpClient.post("/data_backend/map/result", payload)
        .then(function (response) {
          if (response.data["finished"]) {
            // no need to get further results:
            that.map_is_in_progess = false
          }

          const progress = response.data["progress"]

          that.show_loading_bar = !progress.embeddings_available
          that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
          that.progress_step_title = progress.step_title

          if (that.appStateStore.schema.thumbnail_image) {
            that.$refs.embedding_map.pointSizeFactor = 3.0
            that.$refs.embedding_map.maxOpacity = 1.0
          } else {
            that.$refs.embedding_map.pointSizeFactor = 1.0
            that.$refs.embedding_map.maxOpacity = 0.7
          }

          const results = response.data["results"]
          if (results) {
            const results_per_point = results["per_point_data"]
            if (results_per_point["hover_label_data"] && results_per_point["hover_label_data"].length > 0) {
              that.map_item_details = results_per_point["hover_label_data"]
              that.$refs.embedding_map.itemDetails = results_per_point["hover_label_data"]
              that.search_results = results_per_point["hover_label_data"]
              that.fields_already_received.push('hover_label_data')
            }

            if (results_per_point["point_sizes"] && results_per_point["point_sizes"].length > 0) {
              that.$refs.embedding_map.pointSizes = normalizeArrayMedianGamma(results_per_point["point_sizes"], 2.0)
              that.fields_already_received.push('point_sizes')
            }
            if (results_per_point["scores"] && results_per_point["scores"].length > 0) {
              that.$refs.embedding_map.saturation = normalizeArrayMedianGamma(results_per_point["scores"], 3.0, 0.001)
              that.fields_already_received.push('scores')
              if (that.appStateStore.settings.projection.shape === "score_graph") {
                // for the score graph, the score is already visible as the position
                // -> using full saturation for the color to make it better visible
                that.$refs.embedding_map.saturation = Array(results_per_point["scores"].length).fill(1.0)
              }
            }
            if (results_per_point["cluster_ids"] && results_per_point["cluster_ids"].length > 0) {
              that.$refs.embedding_map.clusterIdsPerPoint = results_per_point["cluster_ids"]
              that.clusterIdsPerPoint = results_per_point["cluster_ids"]
              that.fields_already_received.push('cluster_ids')
            } else if (!that.fields_already_received.includes('cluster_ids')) {
              that.$refs.embedding_map.clusterIdsPerPoint = Array(that.$refs.embedding_map.targetPositionsX.length).fill(-1)
            }

            if (results_per_point["positions_x"] && results_per_point["positions_x"].length > 0) {
              that.$refs.embedding_map.targetPositionsX = results_per_point["positions_x"]
              that.$refs.embedding_map.targetPositionsY = results_per_point["positions_y"]
              that.$refs.embedding_map.updateGeometry()
            }

            if (results["texture_atlas_path"] && results["texture_atlas_path"] !== "loading") {
              const image = new Image()
              image.src = 'data_backend/map/texture_atlas/' + results["texture_atlas_path"]
              image.onload = () => {
                that.$refs.embedding_map.textureAtlas = image
                that.$refs.embedding_map.thumbnailSpriteSize = that.appStateStore.settings.search.thumbnail_sprite_size
                that.$refs.embedding_map.updateGeometry()
              }
              that.fields_already_received.push('texture_atlas_path')
            } else if (results["texture_atlas_path"] && results["texture_atlas_path"] === "loading") {
              that.$refs.embedding_map.textureAtlas = null
            }

            if (results["clusters"]) {
              that.$refs.embedding_map.clusterData = results["clusters"]
              that.cluster_data = results["clusters"]
              that.fields_already_received.push('clusters')
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
              that.fields_already_received.push('search_result_score_info')
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
        .finally(function() {
          setTimeout(function() {
            that.request_mapping_progress()
          }.bind(this), 100);
        })
    },
    narrow_down_on_cluster(cluster_item) {
      this.appStateStore.settings.search.search_type = 'cluster'
      this.appStateStore.settings.search.cluster_origin_map_id = this.map_id
      this.appStateStore.settings.search.cluster_id = cluster_item.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = cluster_item.title
      this.request_search_results()
    },
    show_collection_as_map(collection) {
      this.appStateStore.settings.search.search_type = 'collection'
      this.appStateStore.settings.search.collection_id = collection.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = collection.name
      this.request_search_results()
    },
    recommend_items_for_collection(collection) {
      this.appStateStore.settings.search.search_type = 'recommended_for_collection'
      this.appStateStore.settings.search.collection_id = collection.id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.search.origin_display_name = collection.name
      this.request_search_results()
    },
    show_document_details(pointIdx) {
      this.selectedDocumentIdx = pointIdx
      this.$refs.embedding_map.selectedPointIdx = pointIdx
    },
    show_document_details_by_id(item_id) {
      for (const i of Array(this.map_item_details.length).keys()) {
        if (this.map_item_details[i]._id == item_id) {
          this.selectedDocumentIdx = i
          this.$refs.embedding_map.selectedPointIdx = i
          break
        }
      }
    },
    showSimilarItems() {
      this.appStateStore.settings.search.search_type = 'similar_to_item'
      this.appStateStore.settings.search.similar_to_item_id = this.map_item_details[this.selectedDocumentIdx]._id
      this.appStateStore.settings.search.all_field_query = ""
      this.appStateStore.settings.search.all_field_query_negative = ""
      this.appStateStore.settings.projection.shape = "1d_plus_distance_polar"
      const title_func = this.$refs.embedding_map.hover_label_rendering.title
      this.appStateStore.settings.search.origin_display_name = title_func(this.map_item_details[this.selectedDocumentIdx])
      this.request_search_results()
    },
    close_document_details() {
      this.selectedDocumentIdx = -1
      this.$refs.embedding_map.selectedPointIdx = -1
      this.selectedDocumentDetails = null
    },
    updateMapPassiveMargin() {
      if (window.innerWidth > 768) {
        this.$refs.embedding_map.passiveMarginsLRTB = [
          this.$refs.left_column.getBoundingClientRect().right + 50,
          50,
          50,
          150
        ]
      } else {
        this.$refs.embedding_map.passiveMarginsLRTB = [
          50,
          50,
          250,
          50
        ]
      }
    },
    create_item_collection(name) {
      const that = this
      const create_collection_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
        name: name,
      }
      httpClient.post("/organization_backend/add_item_collection", create_collection_body)
        .then(function (response) {
          that.appStateStore.collections.push(response.data)
        })
    },
    delete_item_collection(collection_id) {
      const that = this
      const delete_collection_body = {
        collection_id: collection_id,
      }
      httpClient.post("/organization_backend/delete_item_collection", delete_collection_body)
        .then(function (response) {
          let index_to_be_removed = null
          let i = 0
          for (const collection of that.appStateStore.collections) {
            if (collection.id == collection_id) {
              index_to_be_removed = i
              break
            }
            i += 1
          }
          if (index_to_be_removed !== null) {
            that.appStateStore.collections.splice(index_to_be_removed, 1)
          }
        })
    },
    add_item_to_collection(item_index, collection_id, is_positive) {
      const that = this
      let collection = null
      for (const col of this.collections) {
        if (col.id === collection_id) {
          collection = col
          break
        }
      }
      if (!collection) return;

      this.last_used_collection_id = collection.id
      const item_id = this.map_item_details[item_index]._id
      if (is_positive) {
        if (collection.positive_ids.includes(item_id)) return;
      } else {
        if (collection.negative_ids.includes(item_id)) return;
      }
      const add_item_to_collection_body = {
        collection_id: collection.id,
        item_id: item_id,
        is_positive: is_positive,
      }
      httpClient.post("/organization_backend/add_item_to_collection", add_item_to_collection_body)
        .then(function (response) {
          if (is_positive) {
            collection.positive_ids.push(item_id)
          } else {
            collection.negative_ids.push(item_id)
          }
        })
    },
    store_current_map() {
      const that = this
      const entry_name = this.get_current_map_name()
      if (!entry_name) return;
      const store_map_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
        name: entry_name,
        map_id: this.map_id,
      }
      httpClient.post("/data_backend/map/store", store_map_body)
        .then(function (response) {
          that.stored_maps.push(response.data)
        })
    },
    delete_stored_map(stored_map_id) {
      const that = this
      const delete_stored_map_body = {
        stored_map_id: stored_map_id,
      }
      httpClient.post("/organization_backend/delete_stored_map", delete_stored_map_body)
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

      httpClient.post("/data_backend/stored_map/parameters_and_search_results", body)
        .then(function (response) {
          const parameters = response.data.parameters
          that.appStateStore.settings = parameters

          // now done when map results are received
          //that.show_received_search_results(response.data)
        })

      that.map_viewport_is_adjusted = false
      that.map_is_in_progess = true
      that.request_mapping_progress()
    },
    evaluate_url_query_parameters() {
      // this is almost the first thing that is done when the page is being loaded
      // most importantly, it initializes the schema_id, which then triggers other stuff
      const queryParams = new URLSearchParams(window.location.search);
      if (queryParams.get("schema_id") === null) {
        this.appStateStore.settings.schema_id = 1
        const emptyQueryParams = new URLSearchParams();
        emptyQueryParams.set("schema_id", this.appStateStore.settings.schema_id);
        history.replaceState(null, null, "?" + emptyQueryParams.toString());
      } else if (queryParams.get("schema_id") === String(this.appStateStore.settings.schema_id)) {
        // If this method was called because the user pressed the back arrow in the browser and
        // the schema is the same, the stored_map might be different.
        // In this case, load it here:
        // (in any other case, the stored map is loaded after the schema object is loaded)
        if (queryParams.get("map_id")) {
          this.show_stored_map(queryParams.get("map_id"))
        }
      } else {
        // there is a new schema_id in the parameters:
        this.appStateStore.settings.schema_id = parseInt(queryParams.get("schema_id"))
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
        maxElements = Math.max(maxElements, this.search_result_score_info[score_info_title].scores.length)
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
              x: 'center',
              y: 'top'
            },
          }
        })
        i += 1
      }
      this.score_info_chart = new Chart(this.$refs.score_info_chart, {
        type: 'line',
        data: {
          labels: [...Array(maxElements).keys()],
          datasets: datasets,
        },
        options: {
          plugins: {
            annotation: {
              annotations: annotations
            }
          }
        }
      });
    },
    on_schema_id_change() {
      const that = this

      that.appStateStore.schema = null
      this.reset_search_results_and_map()

      httpClient.post("/organization_backend/object_schema", {schema_id: this.appStateStore.settings.schema_id})
        .then(function (response) {
          that.appStateStore.schema = response.data

          const result_list_rendering = that.appStateStore.schema.result_list_rendering
          for (const field of ['title', 'subtitle', 'body', 'image', 'url']) {
            result_list_rendering[field] = eval(result_list_rendering[field])
          }
          that.result_list_rendering = result_list_rendering

          const collection_list_rendering = that.appStateStore.schema.collection_list_rendering
          for (const field of ['title', 'subtitle', 'body', 'image', 'url']) {
            collection_list_rendering[field] = eval(collection_list_rendering[field])
          }
          that.appStateStore.collection_list_rendering = collection_list_rendering

          const hover_label_rendering = that.appStateStore.schema.hover_label_rendering
          for (const field of ['title', 'subtitle', 'body', 'image']) {
            hover_label_rendering[field] = hover_label_rendering[field] ? eval(hover_label_rendering[field]) : ((item) => "")
          }
          that.$refs.embedding_map.hover_label_rendering = hover_label_rendering

          const queryParams = new URLSearchParams(window.location.search);
          if (queryParams.get("schema_id") === String(that.appStateStore.settings.schema_id) && queryParams.get("map_id")) {
            that.show_stored_map(queryParams.get("map_id"))
          }
        })

      this.search_history = []
      const get_history_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
      }
      httpClient.post("/organization_backend/get_search_history", get_history_body)
        .then(function (response) {
          that.search_history = response.data
        })

      this.appStateStore.collections = []
      const get_collections_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
      }
      httpClient.post("/organization_backend/get_item_collections", get_collections_body)
        .then(function (response) {
          that.appStateStore.collections = response.data
        })

      this.stored_maps = []
      const get_stored_maps_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
      }
      httpClient.post("/organization_backend/get_stored_maps", get_stored_maps_body)
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
    "appStateStore.settings.schema_id" () {
        this.on_schema_id_change()
    },
  },
}

</script>

<template>
    <main class="overflow-hidden">

      <EmbeddingMap ref="embedding_map" class="absolute top-0 w-screen h-screen"
        :appStateStore="appState"
        @cluster_selected="narrow_down_on_cluster"
        @point_selected="show_document_details"
        @cluster_hovered="(cluster_id) => appState.highlighted_cluster_id = cluster_id"
        @cluster_hover_end="appState.highlighted_cluster_id = null"
        />

      <div v-if="appState.show_timings" class="absolute bottom-0 right-0 text-right">
        <!-- timings -->
        <ul role="list">
            <li v-for="item in search_timings" :key="item.part" class="text-gray-300">
              {{ item.part }}: {{ item.duration.toFixed(2) }} s
            </li>
          </ul>
          <hr>
          <ul role="list">
            <li v-for="item in map_timings" :key="item.part" class="text-gray-300">
              {{ item.part }}: {{ item.duration.toFixed(2) }} s
            </li>
          </ul>
      </div>

      <!-- content area -->
      <div class="relative h-screen mr-auto max-w-7xl px-3 pt-6 pb-20 md:pt-6 md:pb-6 xl:px-12 grid grid-cols-1 md:grid-cols-2 gap-4 min-h-0 min-w-0 overflow-hidden pointer-events-none"
        style="grid-auto-rows: minmax(auto, min-content);">

        <!-- left column -->
        <div ref="left_column" class="flex flex-col overflow-hidden pointer-events-none">

          <!-- search card -->
          <SearchArea @request_search_results="request_search_results" @reset_search_box="reset_search_box"
            class="flex-none rounded-md shadow-sm bg-white p-3 pointer-events-auto"></SearchArea>

          <!-- tab box -->
          <div class="flex-initial flex flex-col overflow-hidden mt-3 rounded-md shadow-sm bg-white pointer-events-auto">
            <div class="flex-none flex flex-row gap-1 py-3 mx-3 text-gray-500">
              <button @click="selected_tab = 'map'" :class="{'text-blue-500': selected_tab === 'map'}" class="flex-none px-5">
                ◯
              </button>
              <button @click="selected_tab = 'results'" :class="{'text-blue-500': selected_tab === 'results'}" class="flex-1">
                Results
              </button>
              <button @click="selected_tab = 'history'" :class="{'text-blue-500': selected_tab === 'history'}" class="flex-1">
                History
              </button>
              <button @click="selected_tab = 'maps'" :class="{'text-blue-500': selected_tab === 'maps'}" class="flex-1">
                Maps
              </button>
              <button @click="selected_tab = 'collections'" :class="{'text-blue-500': selected_tab === 'collections'}" class="flex-1">
                Collections
              </button>
            </div>
            <hr v-if="selected_tab !== 'map'" class="h-px bg-gray-200 border-0">

            <div class="flex-initial overflow-y-auto px-3" style="min-height: 0;">
              <!-- result list -->
              <div v-if="selected_tab === 'results'">

                <div v-if="appState.debug_autocut">
                  <canvas ref="score_info_chart"></canvas>
                  <div v-if="search_result_score_info">
                    <div v-for="score_info_title in Object.keys(search_result_score_info)" class="text-xs">
                      {{ score_info_title }} <br>
                      Max score: {{ search_result_score_info[score_info_title].max_score.toFixed(2) }},
                      Min score: {{ search_result_score_info[score_info_title].min_score.toFixed(2) }},
                      Cutoff Index: {{ search_result_score_info[score_info_title].cutoff_index }},
                      Reason: {{ search_result_score_info[score_info_title].reason }}
                      <div v-for="item_id in search_result_score_info[score_info_title].positive_examples" :key="'example' + item_id" class="justify-between pb-3">
                        <CollectionListItem :item_id="item_id" :is_positive="true">
                        </CollectionListItem>
                      </div>
                      <div v-for="item_id in search_result_score_info[score_info_title].negative_examples" :key="'example' + item_id" class="justify-between pb-3">
                        <CollectionListItem :item_id="item_id" :is_positive="false">
                        </CollectionListItem>
                      </div>
                    </div>
                  </div>
                </div>

                <div v-if="search_results.length !== 0" class="flex flex-row items-center mt-2 ml-2">
                  <span class="flex-none mr-2 text-gray-500">Cluster:</span>
                  <select v-model="appState.selected_cluster_id" class="flex-1 text-gray-500 text-md border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
                    <option :value="null" selected>All</option>
                    <option v-for="cluster in cluster_data" :value="cluster.id" selected>{{ cluster.title }}</option>
                  </select>
                </div>

                <ul v-if="search_results.length !== 0" role="list" class="pt-1">
                  <li v-for="item in search_results.filter((result, i) => (appState.selected_cluster_id == null || clusterIdsPerPoint[i] == appState.selected_cluster_id)).slice(0, 10)" :key="item._id" class="justify-between pb-3">
                    <ResultListItem :initial_item="item" :rendering="result_list_rendering" :schema="appState.schema"
                      @mouseenter="appState.highlighted_item_id = item._id"
                      @mouseleave="appState.highlighted_item_id = null"
                      @mousedown="show_document_details_by_id(item._id)"
                    ></ResultListItem>
                  </li>
                </ul>
                <div v-if="search_results.length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Results Yet</p>
                </div>
              </div>

              <!-- history -->
              <div v-if="selected_tab === 'history'">
                <ul v-if="Object.keys(search_history).length !== 0" role="list" class="pt-3">
                  <li v-for="history_item in search_history.slice().reverse()" :key="history_item.id" class="justify-between pb-3">
                    <div class="flex flex-row gap-3">
                      <span class="text-gray-500 font-medium" v-html="history_item.name"></span>
                      <div class="flex-1"></div>
                      <button @click="run_search_from_history(history_item)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Run again</button>
                    </div>
                  </li>
                </ul>
                <div v-if="Object.keys(search_history).length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No History Yet</p>
                </div>
              </div>

              <!-- maps -->
              <div v-if="selected_tab === 'maps'">
                <div class="my-2 flex items-stretch">
                  <button
                    class="flex-auto px-2 rounded-md border-0 py-1.5 text-gray-900 ring-1
                      ring-inset ring-gray-300 placeholder:text-gray-400
                      focus:ring-2 focus:ring-inset focus:ring-blue-400
                      sm:text-sm sm:leading-6 shadow-sm"
                    type="button" @click="store_current_map">
                    Add Current Map
                  </button>
                </div>

                <ul v-if="Object.keys(stored_maps).length !== 0" role="list" class="pt-3">
                  <li v-for="stored_map in stored_maps" :key="stored_map.name" class="justify-between pb-3">
                    <div class="flex flex-row gap-3">
                      <span class="text-gray-500 font-medium">{{ stored_map.name }}</span>
                      <div class="flex-1"></div>
                      <button @click="delete_stored_map(stored_map.id)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Delete</button>
                      <button @click="show_stored_map(stored_map.id)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
                    </div>
                  </li>
                </ul>
                <div v-if="Object.keys(stored_maps).length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Stored Maps Yet</p>
                </div>
              </div>

              <!-- collections -->
              <div v-if="selected_tab === 'collections'">
                <div class="my-2 flex items-stretch">
                  <input ref="new_collection_name"
                    type="text"
                    class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 ring-1
                      ring-inset ring-gray-300 placeholder:text-gray-400
                      focus:ring-2 focus:ring-inset focus:ring-blue-400
                      sm:text-sm sm:leading-6 shadow-sm"
                    placeholder="Collection Name"/>
                  <button
                    class="px-2 rounded-r-md border-0 py-1.5 text-gray-900 ring-1
                      ring-inset ring-gray-300 placeholder:text-gray-400
                      focus:ring-2 focus:ring-inset focus:ring-blue-400
                      sm:text-sm sm:leading-6 shadow-sm"
                    type="button" @click="create_item_collection($refs.new_collection_name.value); $refs.new_collection_name.value = ''">
                    Create
                  </button>
                </div>

                <ul v-if="Object.keys(appState.collections).length !== 0" role="list" class="pt-3">
                  <Collection v-for="collection in appState.collections" :collection="collection" :key="collection.id"
                    @delete_item_collection="delete_item_collection"
                    @recommend_items_for_collection="recommend_items_for_collection"
                    @show_collection_as_map="show_collection_as_map"
                    class="justify-between pb-3">
                  </Collection>
                </ul>
                <div v-if="Object.keys(appState.collections).length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Results Yet</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- right column (e.g. for showing box with details for selected result) -->
        <div ref="right_column" class="flex flex-col overflow-hidden pointer-events-none">

          <div v-if="selectedDocumentIdx !== -1 && map_item_details.length > selectedDocumentIdx" class="flex-initial flex overflow-hidden pointer-events-auto w-full">
            <ObjectDetailsModal :initial_item="map_item_details[selectedDocumentIdx]" :schema="appState.schema"
              :collections="appState.collections" :last_used_collection_id="last_used_collection_id"
              @addToPositives="(selected_collection_id) => { add_item_to_collection(selectedDocumentIdx, selected_collection_id, true) }"
              @addToNegatives="(selected_collection_id) => { add_item_to_collection(selectedDocumentIdx, selected_collection_id, false) }"
              @showSimilarItems="showSimilarItems"
              @close="close_document_details"
            ></ObjectDetailsModal>
          </div>

          <div v-if="show_loading_bar" class="flex-1 flex flex-col w-full justify-center">
            <span class="self-center text-gray-400 font-bold">{{ progress_step_title }}</span>
            <div class="self-center w-1/5 mt-2 bg-gray-400/50 rounded-full h-2.5">
              <div class="bg-blue-400 h-2.5 rounded-full" :style="{'width': (progress * 100).toFixed(0) + '%'}"></div>
            </div>
          </div>
        </div>

      </div>

      <!--  -->
    </main>
</template>

<style scoped></style>
