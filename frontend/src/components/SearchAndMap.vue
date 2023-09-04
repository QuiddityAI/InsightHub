<script setup>
import EmbeddingMap from './EmbeddingMap.vue';
import Parameters from './Parameters.vue';
import ResultListItem from './ResultListItem.vue';
import ObjectDetailsModal from './ObjectDetailsModal.vue';
import CollectionListItem from './CollectionListItem.vue';
import { AdjustmentsHorizontalIcon } from '@heroicons/vue/24/outline'
</script>

<script>

import httpClient from '../api/httpClient';

import { normalizeArray, normalizeArrayMedianGamma } from '../utils/utils'

class FieldType {
  static VECTOR = "VECTOR"
}

export default {
  data() {
    return {
      // input:
      query: "",

      // results:
      search_results: [],
      search_list_rendering: {},
      map_task_id: null,
      map_item_details: [],

      search_timings: "",
      map_timings: "",

      // mapping progress:
      map_is_in_progess: false,
      show_loading_bar: false,
      map_viewport_is_adjusted: false,
      progress: 0.0,
      progress_step_title: "",

      // selection:
      selectedDocumentIdx: -1,
      selectedDocumentDetails: null,

      // tabs:
      selected_tab: "map",

      // lists:
      lists: {
        default: {
          title: "Favorites",
          positives: [{title: "Foo Bar", issued_year: 2017, container_title: "Some Journal"}, {title: "Foo Bar", issued_year: 2017, container_title: "Some Journal"}],
          negatives: [{title: "Foo Bar", issued_year: 2017, container_title: "Some Journal"}],
        },
        mxene_research: {
          title: "MXene Research",
          positives: [],
          negatives: [],
        },
        cancer_research: {
          title: "Cancer Research",
          positives: [],
          negatives: [],
        },
      },

      // settings:
      show_settings: false,
      available_databases: [],
      database_information: {},
      selected_database: null,
      selected_schema: {},
    }
  },
  methods: {
    reset_search_results_and_map() {
      // results:
      this.search_results = []
      this.search_list_rendering = {}
      this.map_task_id = null
      this.map_item_details = []

      this.map_timings = []
      this.search_timings = []

      // mapping progress:
      this.map_viewport_is_adjusted = false
      this.show_loading_bar = false
      this.map_viewport_is_adjusted = false
      this.progress = 0.0
      this.progress_step_title = ""

      // map:
      this.$refs.embedding_map.resetData()
      this.$refs.embedding_map.resetPanAndZoom()

      // selection:
      this.selectedDocumentIdx = -1
      this.selectedDocumentDetails = null
    },
    request_search_results() {
      const that = this

      this.reset_search_results_and_map()

      if (!this.query) return;

      this.selected_tab = "results"

      const payload = this.$refs.parameters_area.get_parameters()
      payload.schema_id = this.selected_database
      payload.query = this.query

      httpClient.post("/data_backend/search_list_result", payload)
        .then(function (response) {
          that.search_results = response.data["items"]
          const rendering = response.data["rendering"]
          for (const field of ['title', 'subtitle', 'body', 'image', 'url']) {
            rendering[field] = eval(rendering[field])
          }
          that.search_list_rendering = rendering
          that.search_timings = response.data["timings"]

          that.request_map()
        })
    },
    request_map() {
      const that = this

      const payload = this.$refs.parameters_area.get_parameters()
      payload.schema_id = this.selected_database
      payload.query = this.query

      httpClient.post("/data_backend/map", payload)
        .then(function (response) {
          that.map_task_id = response.data["task_id"]
          that.map_viewport_is_adjusted = false
          that.map_is_in_progess = true
          that.request_mapping_progress()
        })
    },
    request_mapping_progress() {
      const that = this

      if (!this.map_task_id || !this.map_is_in_progess) return;

      const payload = {
        task_id: this.map_task_id,
      }
      httpClient.post("/data_backend/map/result", payload)
        .then(function (response) {
          const mappingIsFinished = response.data["finished"]

          const result = response.data["result"]

          if (mappingIsFinished) {
            // no need to get further results:
            that.map_is_in_progess = false

            const rendering = result["rendering"]
            for (const field of ['hover_label']) {
              rendering[field] = eval(rendering[field])
            }
            that.$refs.embedding_map.rendering = rendering

            if (result["texture_atlas_path"]) {
              const image = new Image()
              image.src = 'data_backend/map/texture_atlas/' + result["texture_atlas_path"]
              image.onload = () => {
                that.$refs.embedding_map.textureAtlas = image
                that.$refs.embedding_map.updateGeometry()
              }

            }

            // get map details (titles of all points etc.):
            httpClient.post("/data_backend/map/details", payload)
              .then(function (response) {
                that.map_item_details = response.data
                that.$refs.embedding_map.itemDetails = response.data
              })
              .catch(function (error) {
                console.log(error)
              })
          }

          const progress = response.data["progress"]

          that.show_loading_bar = !progress.embeddings_available
          that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
          that.progress_step_title = progress.step_title

          if (result) {
            that.$refs.embedding_map.targetPositionsX = result["per_point_data"]["positions_x"]
            that.$refs.embedding_map.targetPositionsY = result["per_point_data"]["positions_y"]
            that.$refs.embedding_map.clusterIdsPerPoint = result["per_point_data"]["cluster_ids"]
            that.$refs.embedding_map.pointSizes = normalizeArrayMedianGamma(result["per_point_data"]["point_sizes"])
            that.$refs.embedding_map.saturation = normalizeArray(result["per_point_data"]["distances"], 3.0)

            that.$refs.embedding_map.clusterData = result["cluster_data"]

            if (that.map_viewport_is_adjusted) {
              that.$refs.embedding_map.centerAndFitDataToActiveAreaSmooth()
            } else {
              that.$refs.embedding_map.resetPanAndZoom()
              that.$refs.embedding_map.centerAndFitDataToActiveAreaInstant()
              that.map_viewport_is_adjusted = true
            }
            that.$refs.embedding_map.updateGeometry()

            that.map_timings = result["timings"]
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
      this.query = `cluster_id: ${cluster_item.uid} (${cluster_item.title})`
      this.request_search_results()
    },
    show_document_details(pointIdx) {
      const that = this
      this.selectedDocumentIdx = pointIdx
      this.$refs.embedding_map.selectedPointIdx = pointIdx

      const payload = {
        task_id: this.map_task_id,
        index: this.selectedDocumentIdx,
      }
      httpClient.post("/data_backend/document/details", payload)
        .then(function (response) {
          that.selectedDocumentDetails = response.data
        })
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
  },
  watch: {
    selected_database: function(val) {
      const that = this
      httpClient.post("/organization_backend/object_schema", {schema_id: this.selected_database})
        .then(function (response) {
          that.selected_schema = response.data
          that.$refs.parameters_area.available_vector_fields = []
          for (const field_identifier in that.selected_schema.object_fields) {
            const field = that.selected_schema.object_fields[field_identifier]
            //if (field.is_available_for_search && field.field_type == FieldType.VECTOR) {
            if (field.field_type == FieldType.VECTOR) {
              that.$refs.parameters_area.available_vector_fields.push(field.identifier)
            }
            if (that.$refs.parameters_area.available_vector_fields.length > 0) {
              that.$refs.parameters_area.selected_search_vector_field = that.$refs.parameters_area.available_vector_fields[0]
              that.$refs.parameters_area.selected_map_vector_field = that.$refs.parameters_area.available_vector_fields[0]
            } else {
              that.$refs.parameters_area.selected_search_vector_field = null
              that.$refs.parameters_area.selected_map_vector_field = null
            }
          }
        })
    }
  },
  mounted() {
    this.updateMapPassiveMargin()
    window.addEventListener("resize", this.updateMapPassiveMargin)

    const that = this
    httpClient.post("/organization_backend/available_schemas", {organization_id: -1})
      .then(function (response) {
        that.available_databases = response.data
        that.database_information = {}
        for (const database of that.available_databases) {
          that.database_information[database.id] = database.short_description
        }
        that.selected_database = 1
      })
  },
}

</script>

<template>
    <main class="overflow-hidden">

      <EmbeddingMap ref="embedding_map" class="absolute top-0 w-screen h-screen"
        @cluster_selected="narrow_down_on_cluster"
        @point_selected="show_document_details"/>

      <div v-if="$refs.parameters_area ? $refs.parameters_area.show_timings : false" class="absolute bottom-0 right-0 text-right">
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
          <div class="flex-none rounded-md shadow-sm bg-white p-3  pointer-events-auto">
            <div class="flex justify-between">
              <select v-model="selected_database" class="pl-2 pr-8 pt-1 pb-1 mb-2 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
                <option v-for="item in available_databases" :value="item.id" selected>{{ item.name_plural }}</option>
              </select>
              <span class="pl-2 pr-2 pt-1 pb-1 mb-2 text-gray-500 text-sm text-right">{{ database_information[selected_database] }}</span>
            </div>

            <div class="flex">
              <!-- note: search event is not standard -->
              <input type="search" name="search" @search="request_search_results" v-model="query"
                placeholder="Search"
                class="w-full rounded-md border-0 py-1.5 text-gray-900 ring-1
              ring-inset ring-gray-300 placeholder:text-gray-400
              focus:ring-2 focus:ring-inset focus:ring-indigo-600
              sm:text-sm sm:leading-6 shadow-sm" />
              <button @click="show_settings = !show_settings" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': show_settings, 'text-gray-500': !show_settings }">
                <AdjustmentsHorizontalIcon></AdjustmentsHorizontalIcon>
              </button>
            </div>

            <Parameters ref="parameters_area" v-show="show_settings" class="mt-3"></Parameters>
          </div>

          <!-- tab box -->
          <div class="flex-initial flex flex-col overflow-hidden mt-3 rounded-md shadow-sm bg-white pointer-events-auto">
            <div class="flex-none flex flex-row gap-1 py-3 text-gray-500">
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
              <button @click="selected_tab = 'lists'" :class="{'text-blue-500': selected_tab === 'lists'}" class="flex-1">
                Lists
              </button>
            </div>
            <hr v-if="selected_tab !== 'map'" class="h-px bg-gray-200 border-0">

            <div class="flex-initial overflow-y-auto px-3" style="min-height: 0;">
              <!-- result list -->
              <div v-if="selected_tab === 'results'">
                <ul v-if="search_results.length !== 0" role="list" class="pt-3">
                  <li v-for="item in search_results" :key="item.title" class="justify-between pb-3">
                    <ResultListItem :item="item" :rendering="search_list_rendering"></ResultListItem>
                  </li>
                </ul>
                <div v-if="search_results.length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Results Yet</p>
                </div>
              </div>

              <!-- history -->
              <div v-if="selected_tab === 'history'">
                <div class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">Search History</p>
                </div>
              </div>

              <!-- history -->
              <div v-if="selected_tab === 'maps'">
                <div class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">Store Maps<br>(with annotations and custom clustering)</p>
                </div>
              </div>

              <!-- lists -->
              <div v-if="selected_tab === 'lists'">
                <ul v-if="Object.keys(lists).length !== 0" role="list" class="pt-3">
                  <li v-for="list in lists" :key="list.title" class="justify-between pb-3">
                    <div class="flex flex-row gap-3">
                      <span class="text-gray-500 font-medium">{{ list.title }}</span>
                      <div class="flex-1"></div>
                      <button class="text-sm text-gray-500 font-light hover:text-blue-500/50">Recommend Similar</button>
                      <button class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
                    </div>
                    <ul class="pt-2">
                      <li v-for="(item, index) in list.positives" :key="item.title" class="justify-between pb-2">
                        <CollectionListItem :item="item" :is-positive="true" @remove="list.positives.splice(index, 1)">
                        </CollectionListItem>
                      </li>
                    </ul>
                    <ul class="pt-2">
                      <li v-for="(item, index) in list.negatives" :key="item.title" class="justify-between pb-2">
                        <CollectionListItem :item="item" :is-positive="false" @remove="list.negatives.splice(index, 1)">
                        </CollectionListItem>
                      </li>
                    </ul>
                  </li>
                </ul>
                <div v-if="Object.keys(lists).length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Results Yet</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- right column (e.g. for showing box with details for selected result) -->
        <div ref="right_column" class="flex flex-col overflow-hidden pointer-events-none">

          <div v-if="selectedDocumentIdx !== -1 && map_item_details.length > selectedDocumentIdx" class="flex-initial flex overflow-hidden pointer-events-auto w-full">
            <ObjectDetailsModal :item="map_item_details[selectedDocumentIdx]" :abstract="selectedDocumentDetails ? selectedDocumentDetails.abstract : 'loading...'"
              @addToPositives="lists.default.positives.push(map_item_details[selectedDocumentIdx])"
              @addToNegatives="lists.default.negatives.push(map_item_details[selectedDocumentIdx])"
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
