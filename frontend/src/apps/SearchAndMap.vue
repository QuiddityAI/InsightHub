<script setup>
import cborJs from "https://cdn.jsdelivr.net/npm/cbor-js@0.1.0/+esm"
import Message from 'primevue/message';

import { mapStores } from "pinia"

import { Chart } from "chart.js/auto"
import annotationPlugin from "chartjs-plugin-annotation"
import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline"

import Toast from 'primevue/toast';

import MapWithLabels from "../components/map/MapWithLabels.vue"
import SearchArea from "../components/search/SearchArea.vue"
import ResultListItem from "../components/search/ResultListItem.vue"
import ObjectDetailsModal from "../components/search/ObjectDetailsModal.vue"
import CollectionArea from "../components/collections/CollectionArea.vue"
import CollectionItem from "../components/collections/CollectionItem.vue"
import AddToCollectionButtons from "../components/collections/AddToCollectionButtons.vue"
import StatisticList from "../components/search/StatisticList.vue"

import { httpClient } from "../api/httpClient"
import { FieldType, normalizeArray, normalizeArrayMedianGamma } from "../utils/utils"

import { useAppStateStore } from "../stores/app_state_store"
import { useMapStateStore } from "../stores/map_state_store"
import FilterList from "../components/search/FilterList.vue"
import ResultList from "../components/search/ResultList.vue"
const appState = useAppStateStore()
const mapState = useMapStateStore()

Chart.register(annotationPlugin)
</script>

<script>
export default {
  inject: ["eventBus"],
  data() {
    return {
      // tabs:
      selected_tab: "map",

      score_info_chart: null,
    }
  },
  methods: {
    updateMapPassiveMargin() {
      if (window.innerWidth > 768) {
        this.mapStateStore.passiveMarginsLRTB = [
          this.$refs.left_column.getBoundingClientRect().right + 50,
          50,
          50,
          150,
        ]
      } else {
        this.mapStateStore.passiveMarginsLRTB = [50, 50, 250, 50]
      }
    },
    evaluate_url_query_parameters() {
      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("error") !== null) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: queryParams.get("error") })
      }

      if (queryParams.get("organization_id") === null) {
        this.appStateStore.set_organization_id(1, /* change_history */ false)
        const emptyQueryParams = new URLSearchParams()
        emptyQueryParams.set("organization_id", this.appStateStore.organization_id)
        history.replaceState(null, null, "?" + emptyQueryParams.toString())
      } else if (
        queryParams.get("organization_id") === String(this.appStateStore.organization_id)
      ) {
        // If this method was called because the user pressed the back arrow in the browser and
        // the dataset is the same, the stored_map might be different.
        // In this case, the datasets are still loaded and we can directly load the map:
        if (queryParams.get("map_id")) {
          this.appStateStore.show_stored_map(queryParams.get("map_id"))
        }
      } else {
        // there is a new dataset_id in the parameters:
        this.appStateStore.set_organization_id(parseInt(queryParams.get("organization_id")), /*change history*/ false)
        // if there is a map_id in the parameters, its loaded after all datasets are loaded
      }
    },
    show_score_info_chart() {
      if (this.score_info_chart) this.score_info_chart.destroy()
      const datasets = []
      const annotations = []
      const colors = ["red", "green", "blue", "purple", "fuchsia", "aqua", "yellow", "navy"]
      let i = 0
      let maxElements = 1
      for (const score_info_title in this.appStateStore.search_result_score_info) {
        maxElements = Math.max(
          maxElements,
          this.appStateStore.search_result_score_info[score_info_title].scores.length
        )
        datasets.push({
          label: score_info_title,
          data: this.appStateStore.search_result_score_info[score_info_title].scores,
          borderWidth: 1,
          pointStyle: false,
          borderColor: colors[i],
        })
        annotations.push({
          type: "line",
          mode: "vertical",
          xMax: this.appStateStore.search_result_score_info[score_info_title].cutoff_index,
          xMin: this.appStateStore.search_result_score_info[score_info_title].cutoff_index,
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
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useMapStateStore),
  },
  mounted() {
    const that = this
    this.appStateStore.initialize()
    this.appStateStore.retrieve_current_user()
    this.appStateStore.retrieve_available_organizations(() => {
      this.evaluate_url_query_parameters()
      this.appStateStore.retrieve_stored_maps_history_and_collections()
    })
    this.eventBus.on("datasets_are_loaded", () => {
      const queryParams = new URLSearchParams(window.location.search)
      if (queryParams.get("map_id")) {
        that.appStateStore.show_stored_map(queryParams.get("map_id"))
      }
    })

    this.updateMapPassiveMargin()
    window.addEventListener("resize", this.updateMapPassiveMargin)
    window.addEventListener("popstate", this.evaluate_url_query_parameters)

    this.eventBus.on("show_results_tab", () => {
      this.selected_tab = "results"
    })
    this.eventBus.on("show_score_info_chart", () => {
      this.show_score_info_chart()
    })
  },
  watch: {
    "appStateStore.organization_id"() {
      this.appStateStore.reset_search_results_and_map()
      this.appStateStore.retrieve_stored_maps_history_and_collections()
    },
  },
}
</script>

<template>
  <main class="overflow-hidden">
    <Toast position="top-right"></Toast>
    <MapWithLabels class="absolute top-0 h-screen w-screen"/>

    <div
      v-if="mapState.selected_map_tool === 'lasso'"
      class="absolute bottom-6 right-4 flex flex-row justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <button
        @click="mapState.selection_merging_mode = 'replace'"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'replace',
          'text-gray-400': mapState.selection_merging_mode !== 'replace',
        }">
        <ViewfinderCircleIcon></ViewfinderCircleIcon>
      </button>
      <button
        @click="mapState.selection_merging_mode = 'add'"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'add',
          'text-gray-400': mapState.selection_merging_mode !== 'add',
        }">
        <PlusIcon></PlusIcon>
      </button>
      <button
        @click="mapState.selection_merging_mode = 'remove'"
        class="mr-2 h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selection_merging_mode === 'remove',
          'text-gray-400': mapState.selection_merging_mode !== 'remove',
        }">
        <MinusIcon></MinusIcon>
      </button>
      <div class="h-6 w-6"></div>
    </div>
    <div
      class="absolute bottom-6 right-4 flex flex-col justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <button
        @click="mapState.selected_map_tool = 'drag'; mapState.selection_merging_mode = 'replace'"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selected_map_tool === 'drag',
          'text-gray-400': mapState.selected_map_tool !== 'drag',
        }">
        <CursorArrowRaysIcon></CursorArrowRaysIcon>
      </button>
      <button
        @click="mapState.selected_map_tool = 'lasso'"
        class="h-6 w-6 rounded hover:bg-gray-100"
        :class="{
          'text-blue-600': mapState.selected_map_tool === 'lasso',
          'text-gray-400': mapState.selected_map_tool !== 'lasso',
        }">
        <RectangleGroupIcon></RectangleGroupIcon>
      </button>
    </div>

    <div
      v-if="mapState.selected_point_indexes.length"
      class="absolute bottom-6 right-48 flex flex-row items-center justify-center gap-2 rounded-md bg-white p-2 shadow-sm">
      <span class="mr-2 text-sm text-gray-400">Selection:</span>
      <AddToCollectionButtons
        @addToCollection="appState.add_selected_points_to_collection"
        @removeFromCollection="appState.remove_selected_points_from_collection">
      </AddToCollectionButtons>
      <button
        @click="mapState.selected_point_indexes = []"
        class="h-6 w-6 rounded text-gray-400 hover:bg-red-100">
        <XMarkIcon></XMarkIcon>
      </button>
    </div>

    <div v-if="appState.show_timings" class="absolute bottom-0 right-0 text-right">
      <!-- timings -->
      <ul role="list">
        <li v-for="item in appState.search_timings" :key="item.part" class="text-gray-300">
          {{ item.part }}: {{ item.duration.toFixed(2) }} s
        </li>
      </ul>
      <hr />
      <ul role="list">
        <li v-for="item in appState.map_timings" :key="item.part" class="text-gray-300">
          {{ item.part }}: {{ item.duration.toFixed(2) }} s
        </li>
      </ul>
    </div>

    <!-- content area -->
    <div
      class="pointer-events-none relative mr-auto grid h-screen min-h-0 min-w-0 max-w-7xl grid-cols-1 gap-4 overflow-hidden px-3 pb-20 pt-6 md:grid-cols-2 md:pb-6 md:pt-6 xl:px-12"
      style="grid-auto-rows: minmax(auto, min-content)">
      <!-- left column -->
      <div ref="left_column" class="pointer-events-none flex flex-col overflow-hidden h-[calc(100%-3em)]">
        <!-- search card -->
        <SearchArea
          @request_search_results="appState.request_search_results"
          @reset_search_box="appState.reset_search_box"
          @show_global_map="appState.show_global_map"
          class="pointer-events-auto flex-none rounded-md bg-white p-3 shadow-sm"></SearchArea>

        <!-- tab box -->
        <div
          class="pointer-events-auto mt-3 flex flex-initial flex-col overflow-hidden rounded-md bg-white shadow-sm">
          <div class="mx-3 flex flex-none flex-row gap-1 py-3 text-gray-500">
            <button
              @click="selected_tab = 'map'"
              :class="{ 'text-blue-500': selected_tab === 'map' }"
              class="flex-none px-5">
              ◯
            </button>
            <button
              @click="selected_tab = 'results'"
              :class="{ 'text-blue-500': selected_tab === 'results' }"
              class="flex-1">
              Results
            </button>
            <button
              @click="selected_tab = 'history'"
              :class="{ 'text-blue-500': selected_tab === 'history' }"
              class="flex-1">
              History
            </button>
            <button
              @click="selected_tab = 'maps'"
              :class="{ 'text-blue-500': selected_tab === 'maps' }"
              class="flex-1">
              Maps
            </button>
            <button
              @click="selected_tab = 'collections'; eventBus.emit('collections_tab_is_clicked')"
              :class="{ 'text-blue-500': selected_tab === 'collections' }"
              class="flex-1">
              Collections
            </button>
          </div>
          <hr v-if="selected_tab !== 'map'" class="h-px border-0 bg-gray-200" />

          <div class="flex-initial overflow-y-auto px-3" style="min-height: 0">
            <!-- result list -->
            <div v-if="selected_tab === 'results'">
              <div v-if="appState.debug_autocut">
                <canvas ref="score_info_chart"></canvas>
                <div v-if="search_result_score_info">
                  <div
                    v-for="score_info_title in Object.keys(search_result_score_info)"
                    class="text-xs">
                    {{ score_info_title }} <br />
                    Max score:
                    {{ search_result_score_info[score_info_title].max_score.toFixed(2) }}, Min
                    score:
                    {{ search_result_score_info[score_info_title].min_score.toFixed(2) }},
                    Cutoff Index:
                    {{ search_result_score_info[score_info_title].cutoff_index }}, Reason:
                    {{ search_result_score_info[score_info_title].reason }}
                    <div
                      v-for="item_id in search_result_score_info[score_info_title]
                        .positive_examples"
                      :key="'example' + item_id"
                      class="justify-between pb-3">
                      <CollectionItem :item_id="item_id" :is_positive="true">
                      </CollectionItem>
                    </div>
                    <div
                      v-for="item_id in search_result_score_info[score_info_title]
                        .negative_examples"
                      :key="'example' + item_id"
                      class="justify-between pb-3">
                      <CollectionItem :item_id="item_id" :is_positive="false">
                      </CollectionItem>
                    </div>
                  </div>
                </div>
              </div>

              <FilterList></FilterList>

              <StatisticList></StatisticList>

              <div
                v-if="appState.search_result_ids.length !== 0"
                class="ml-2 mt-1 flex flex-row items-center">
                <span class="mr-2 flex-none text-gray-500">Cluster:</span>
                <div class="h-10">
                  <select
                    v-model="appState.selected_cluster_id"
                    class="h-[90%] text-md flex-1 rounded border-transparent text-gray-500 focus:border-blue-500 focus:ring-blue-500">
                    <option :value="null" selected>All</option>
                    <option v-for="cluster in appState.cluster_data" :value="cluster.id" selected>
                      {{ cluster.title }}
                    </option>
                  </select>
                </div>
              </div>

              <ResultList></ResultList>
            </div>

            <!-- history -->
            <div v-if="selected_tab === 'history'">
              <ul v-if="Object.keys(appState.search_history).length !== 0" role="list" class="pt-3">
                <li
                  v-for="history_item in appState.search_history.slice().reverse()"
                  :key="history_item.id"
                  class="justify-between pb-3">
                  <div class="flex flex-row gap-3">
                    <span class="font-medium text-gray-500" v-html="history_item.display_name"></span>
                    <div class="flex-1"></div>
                    <button
                      @click="appState.run_search_from_history(history_item)"
                      class="text-sm font-light text-gray-500 hover:text-blue-500/50">
                      Run again
                    </button>
                  </div>
                </li>
              </ul>
              <div
                v-if="Object.keys(appState.search_history).length === 0"
                class="flex h-20 flex-col place-content-center text-center">
                <p class="flex-none text-gray-400">No History Yet</p>
              </div>
            </div>

            <!-- maps -->
            <div v-if="selected_tab === 'maps'">
              <Message v-if="!appState.logged_in" severity="warn">
                Log in to store maps
              </Message>

              <div v-if="appState.map_id && appState.logged_in" class="my-2 flex items-stretch">
                <button
                  class="flex-auto rounded-md border-0 px-2 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
                  type="button"
                  @click="appState.store_current_map">
                  Add Current Map
                </button>
              </div>

              <ul v-if="Object.keys(appState.stored_maps).length !== 0" role="list" class="pt-3">
                <li
                  v-for="stored_map in appState.stored_maps"
                  :key="stored_map.name"
                  class="justify-between pb-3">
                  <div class="flex flex-row gap-3">
                    <span class="font-medium text-gray-500">{{ stored_map.name }}</span>
                    <div class="flex-1"></div>
                    <button
                      @click="delete_stored_map(stored_map.id)"
                      class="text-sm font-light text-gray-500 hover:text-blue-500/50">
                      Delete
                    </button>
                    <button
                      @click="appState.show_stored_map(stored_map.id)"
                      class="text-sm font-light text-gray-500 hover:text-blue-500/50">
                      Show Map
                    </button>
                  </div>
                </li>
              </ul>
              <div
                v-if="Object.keys(appState.stored_maps).length === 0"
                class="flex h-20 flex-col place-content-center text-center">
                <p class="flex-none text-gray-400">No Stored Maps Yet</p>
              </div>
            </div>

            <!-- collections -->
            <CollectionArea v-if="selected_tab === 'collections'"> </CollectionArea>
          </div>
        </div>
      </div>

      <!-- right column (e.g. for showing box with details for selected result) -->
      <div
        ref="right_column"
        class="pointer-events-none flex flex-col overflow-hidden md:h-screen">
        <div
          v-if="appState.selected_document_ds_and_id !== null"
          class="pointer-events-auto flex w-full flex-initial overflow-hidden">
          <ObjectDetailsModal
            :initial_item="appState.get_item_by_ds_and_id(appState.selected_document_ds_and_id)"
            :dataset="appState.datasets[appState.selected_document_ds_and_id[0]]"
            @addToCollection="
              (collection_id, class_name, is_positive) => {
                appState.add_item_to_collection(
                  appState.selected_document_ds_and_id,
                  collection_id,
                  class_name,
                  is_positive
                )
              }
            "
            @removeFromCollection="
              (collection_id, class_name) => {
                appState.remove_item_from_collection(
                  appState.selected_document_ds_and_id,
                  collection_id,
                  class_name
                )
              }
            "
            @showSimilarItems="appState.showSimilarItems"
            @close="appState.close_document_details"></ObjectDetailsModal>
        </div>

        <div v-if="appState.show_loading_bar" class="flex w-full flex-1 flex-col justify-center">
          <span class="self-center font-bold text-gray-400">{{ appState.progress_step_title }}</span>
          <div class="mt-2 h-2.5 w-1/5 self-center rounded-full bg-gray-400/50">
            <div
              class="h-2.5 rounded-full bg-blue-400"
              :style="{ width: (appState.progress * 100).toFixed(0) + '%' }"></div>
          </div>
        </div>

        <div
          v-if="!appState.show_loading_bar && !appState.search_result_ids.length"
          class="align-center flex flex-1 flex-col justify-center">
          <div class="mb-6 flex flex-row justify-center">
            <img
              class="h-12"
              :src="appState.organization ? appState.organization.workspace_tool_logo_url : ''" />
          </div>
          <div
            class="mb-2 flex-none text-center pointer-events-auto font-bold text-gray-400"
            v-html="appState.organization ? appState.organization.workspace_tool_intro_text : ''"></div>
        </div>
      </div>
    </div>

    <!-- <div
      v-if="appState.organization ? !appState.organization.workspace_tool_title : true"
      class="absolute -right-3 bottom-4 rounded-xl bg-black py-1 pl-3 pr-5 font-['Lexend'] shadow-sm">
      <span class="font-bold text-white">Quiddity</span>
      <span class="font-light text-gray-200">Workspace</span>
    </div> -->

    <!--  -->
  </main>
</template>

<style scoped></style>
