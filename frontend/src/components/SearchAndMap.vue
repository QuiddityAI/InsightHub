<script setup>
import { mapStores } from 'pinia'

import EmbeddingMap from './EmbeddingMap.vue';
import Parameters from './Parameters.vue';
import ResultListItem from './ResultListItem.vue';
import ObjectDetailsModal from './ObjectDetailsModal.vue';
import CollectionListItem from './CollectionListItem.vue';
import { AdjustmentsHorizontalIcon } from '@heroicons/vue/24/outline'

import { useAppStateStore } from '../stores/settings_store'

const appState = useAppStateStore()

</script>

<script>

import httpClient from '../api/httpClient';

import { normalizeArray, normalizeArrayMedianGamma } from '../utils/utils'

class FieldType {
  static VECTOR = "VECTOR"
  static INTEGER = "INTEGER"
  static FLOAT = "FLOAT"
}

export default {
  data() {
    return {
      // results:
      search_results: [],
      search_list_rendering: {},
      map_id: null,
      map_item_details: [],

      search_timings: "",
      map_timings: "",

      search_history: [],

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

      // collections:
      collections: [],
      last_used_collection_id: null,

      // stored maps:
      stored_maps: [],

      // settings:
      show_settings: false,
      available_databases: [],
      database_information: {},
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
    run_search_from_history(history_item) {
      // schema is already correct in this case
      this.query = history_item.parameters.query
      // TODO: set other search parameters
      this.request_search_results()
    },
    request_search_results() {
      const that = this

      this.reset_search_results_and_map()

      if (!this.appStateStore.settings.search_settings.all_field_query) return;

      this.selected_tab = "results"

      const history_item_body = {
        user_id: 1,  // FIXME: this is hardcoded
        schema_id: this.appStateStore.settings.schema_id,
        name: this.appStateStore.settings.search_settings.all_field_query,  // TODO: doesn't work for other types
        parameters: this.appStateStore.settings,
      }

      httpClient.post("/organization_backend/add_search_history_item", history_item_body)
        .then(function (response) {
          that.search_history.push(response.data)
        })

      httpClient.post("/data_backend/search_list_result", this.appStateStore.settings)
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

      httpClient.post("/data_backend/map", this.appStateStore.settings)
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

      const payload = {
        map_id: this.map_id,
      }
      httpClient.post("/data_backend/map/result", payload)
        .then(function (response) {
          const mappingIsFinished = response.data["finished"]

          const results = response.data["results"]

          if (mappingIsFinished) {
            // no need to get further results:
            that.map_is_in_progess = false

            const hover_label_rendering = response.data["hover_label_rendering"]
            for (const field of ['title', 'subtitle', 'body', 'image']) {
              hover_label_rendering[field] = eval(hover_label_rendering[field])
            }
            that.$refs.embedding_map.hover_label_rendering = hover_label_rendering

            if (results["texture_atlas_path"]) {
              const image = new Image()
              image.src = 'data_backend/map/texture_atlas/' + results["texture_atlas_path"]
              image.onload = () => {
                that.$refs.embedding_map.textureAtlas = image
                that.$refs.embedding_map.updateGeometry()
              }

            }
          }

          const progress = response.data["progress"]

          that.show_loading_bar = !progress.embeddings_available
          that.progress = progress.current_step / Math.max(1, progress.total_steps - 1)
          that.progress_step_title = progress.step_title

          if (results) {
            if (results["per_point_data"]["hover_label_data"]) {
              that.map_item_details = results["per_point_data"]["hover_label_data"]
              that.$refs.embedding_map.itemDetails = results["per_point_data"]["hover_label_data"]
            }

            that.$refs.embedding_map.targetPositionsX = results["per_point_data"]["positions_x"]
            that.$refs.embedding_map.targetPositionsY = results["per_point_data"]["positions_y"]
            that.$refs.embedding_map.clusterIdsPerPoint = results["per_point_data"]["cluster_ids"]
            that.$refs.embedding_map.pointSizes = normalizeArrayMedianGamma(results["per_point_data"]["point_sizes"])
            that.$refs.embedding_map.saturation = normalizeArray(results["per_point_data"]["scores"], 3.0)

            that.$refs.embedding_map.clusterData = results["clusters"]

            if (that.map_viewport_is_adjusted) {
              that.$refs.embedding_map.centerAndFitDataToActiveAreaSmooth()
            } else {
              that.$refs.embedding_map.resetPanAndZoom()
              that.$refs.embedding_map.centerAndFitDataToActiveAreaInstant()
              that.map_viewport_is_adjusted = true
            }
            that.$refs.embedding_map.updateGeometry()

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
      this.query = `cluster_id: ${cluster_item.uid} (${cluster_item.title})`
      this.request_search_results()
    },
    show_document_details(pointIdx) {
      const that = this
      this.selectedDocumentIdx = pointIdx
      this.$refs.embedding_map.selectedPointIdx = pointIdx
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
          that.collections.push(response.data)
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
          for (const collection of that.collections) {
            if (collection.id == collection_id) {
              index_to_be_removed = i
              break
            }
            i += 1
          }
          if (index_to_be_removed !== null) {
            that.collections.splice(index_to_be_removed, 1)
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
      const store_map_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
        name: this.appStateStore.settings.search_settings.query,
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
      const that = this
      this.reset_search_results_and_map()
      that.map_id = stored_map_id
      that.map_viewport_is_adjusted = false
      that.map_is_in_progess = true
      that.request_mapping_progress()
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
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
        that.appStateStore.settings.schema_id = 1
      })
    },
  watch: {
    'appStateStore.settings.schema_id' (newValue, oldValue) {
      const that = this

      this.search_history = []
      const get_history_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
      }
      httpClient.post("/organization_backend/get_search_history", get_history_body)
        .then(function (response) {
          that.search_history = response.data
        })

      this.collections = []
      const get_collections_body = {
        user_id: 1,  // FIXME: hardcoded
        schema_id: this.appStateStore.settings.schema_id,
      }
      httpClient.post("/organization_backend/get_item_collections", get_collections_body)
        .then(function (response) {
          that.collections = response.data
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

      httpClient.post("/organization_backend/object_schema", {schema_id: this.appStateStore.settings.schema_id})
        .then(function (response) {
          that.selected_schema = response.data
          that.appStateStore.available_vector_fields = []
          that.appStateStore.available_number_fields = []
          for (const field_identifier in that.selected_schema.object_fields) {
            const field = that.selected_schema.object_fields[field_identifier]
            //if (field.is_available_for_search && field.field_type == FieldType.VECTOR) {
            if (field.field_type == FieldType.VECTOR) {
              that.appStateStore.available_vector_fields.push(field.identifier)
            } else if (field.field_type == FieldType.INTEGER || field.field_type == FieldType.FLOAT) {
              that.appStateStore.available_number_fields.push(field.identifier)
            }
            if (that.appStateStore.available_vector_fields.length > 0) {
              that.appStateStore.settings.search_settings.search_vector_field = that.appStateStore.available_vector_fields[0]
              that.appStateStore.settings.vectorize_settings.map_vector_field = that.appStateStore.available_vector_fields[0]
            } else {
              that.appStateStore.settings.search_settings.search_vector_field = null
              that.appStateStore.settings.vectorize_settings.map_vector_field = null
            }
            if (that.appStateStore.available_number_fields.length > 0) {
              that.appStateStore.settings.render_settings.point_size_field = that.appStateStore.available_number_fields[0]
            } else {
              that.appStateStore.settings.search_settings.point_size_field = null
            }
          }
        })
    }
  },
}

</script>

<template>
    <main class="overflow-hidden">

      <EmbeddingMap ref="embedding_map" class="absolute top-0 w-screen h-screen"
        @cluster_selected="narrow_down_on_cluster"
        @point_selected="show_document_details"/>

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
          <div class="flex-none rounded-md shadow-sm bg-white p-3  pointer-events-auto">
            <div class="flex justify-between">
              <select v-model="appState.settings.schema_id" class="pl-2 pr-8 pt-1 pb-1 mb-2 text-gray-500 text-sm border-transparent rounded focus:ring-blue-500 focus:border-blue-500">
                <option v-for="item in available_databases" :value="item.id" selected>{{ item.name_plural }}</option>
              </select>
              <span class="pl-2 pr-2 pt-1 pb-1 mb-2 text-gray-500 text-sm text-right">{{ database_information[appState.settings.schema_id] }}</span>
            </div>

            <div class="flex">
              <!-- note: search event is not standard -->
              <input type="search" name="search" @search="request_search_results" v-model="appState.settings.search_settings.all_field_query"
                placeholder="Search"
                class="w-full rounded-md border-0 py-1.5 text-gray-900 ring-1
              ring-inset ring-gray-300 placeholder:text-gray-400
              focus:ring-2 focus:ring-inset focus:ring-blue-400
              sm:text-sm sm:leading-6 shadow-sm" />
              <button @click="show_settings = !show_settings" class="w-8 px-1 ml-1 hover:bg-gray-100 rounded" :class="{ 'text-blue-600': show_settings, 'text-gray-500': !show_settings }">
                <AdjustmentsHorizontalIcon></AdjustmentsHorizontalIcon>
              </button>
            </div>

            <Parameters ref="parameters_area" v-show="show_settings" :schema="selected_schema" class="mt-3"></Parameters>
          </div>

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
                <ul v-if="Object.keys(search_history).length !== 0" role="list" class="pt-3">
                  <li v-for="history_item in search_history.slice().reverse()" :key="history_item.id" class="justify-between pb-3">
                    <div class="flex flex-row gap-3">
                      <span class="text-gray-500 font-medium">{{ history_item.name }}</span>
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

                <ul v-if="Object.keys(collections).length !== 0" role="list" class="pt-3">
                  <li v-for="collection in collections" :key="collection.id" class="justify-between pb-3">
                    <div class="flex flex-row gap-3">
                      <span class="text-gray-500 font-medium">{{ collection.name }}</span>
                      <div class="flex-1"></div>
                      <button @click="delete_item_collection(collection.id)" class="text-sm text-gray-500 font-light hover:text-blue-500/50">Delete</button>
                      <button class="text-sm text-gray-500 font-light hover:text-blue-500/50">Recommend Similar</button>
                      <button class="text-sm text-gray-500 font-light hover:text-blue-500/50">Show Map</button>
                    </div>
                    <ul class="pt-2">
                      <li v-for="(item_id, index) in collection.positive_ids" :key="item_id" class="justify-between pb-2">
                        <CollectionListItem :item_id="item_id" :schema_id="appState.settings.schema_id" :is-positive="true" @remove="collection.positives.splice(index, 1)">
                        </CollectionListItem>
                      </li>
                    </ul>
                    <ul class="pt-2">
                      <li v-for="(item_id, index) in collection.negative_ids" :key="item_id" class="justify-between pb-2">
                        <CollectionListItem :item_id="item_id" :schema_id="appState.settings.schema_id" :is-positive="false" @remove="collection.negatives.splice(index, 1)">
                        </CollectionListItem>
                      </li>
                    </ul>
                  </li>
                </ul>
                <div v-if="Object.keys(collections).length === 0" class="h-20 flex flex-col text-center place-content-center">
                  <p class="flex-none text-gray-400">No Results Yet</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- right column (e.g. for showing box with details for selected result) -->
        <div ref="right_column" class="flex flex-col overflow-hidden pointer-events-none">

          <div v-if="selectedDocumentIdx !== -1 && map_item_details.length > selectedDocumentIdx" class="flex-initial flex overflow-hidden pointer-events-auto w-full">
            <ObjectDetailsModal :initial_item="map_item_details[selectedDocumentIdx]" :schema="selected_schema"
              :collections="collections" :last_used_collection_id="last_used_collection_id"
              @addToPositives="(selected_collection_id) => { add_item_to_collection(selectedDocumentIdx, selected_collection_id, true) }"
              @addToNegatives="(selected_collection_id) => { add_item_to_collection(selectedDocumentIdx, selected_collection_id, false) }"
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
