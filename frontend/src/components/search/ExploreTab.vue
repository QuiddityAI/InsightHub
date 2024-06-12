<script setup>
import {
  CursorArrowRaysIcon,
  RectangleGroupIcon,
  PlusIcon,
  MinusIcon,
  ViewfinderCircleIcon,
  XMarkIcon,
} from "@heroicons/vue/24/outline"

import Toast from 'primevue/toast';
import Dialog from 'primevue/dialog';
import Button from 'primevue/button';
import DynamicDialog from 'primevue/dynamicdialog'
import OverlayPanel from "primevue/overlaypanel";
import Message from 'primevue/message';

import SearchArea from "../search/SearchArea.vue"
import FilterList from "../search/FilterList.vue"
import RangeFilterList from "../search/RangeFilterList.vue"
import ResultList from "../search/ResultList.vue"
import ObjectDetailsModal from "../search/ObjectDetailsModal.vue"
import CollectionArea from "../collections/CollectionArea.vue"
import CollectionItem from "../collections/CollectionItem.vue"
import StatisticList from "../search/StatisticList.vue"
import DatasetsArea from "../datasets/DatasetsArea.vue"
import ChatList from "../chats/ChatList.vue"

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    use_single_column() {
      return window.innerWidth < 768 || (this.selected_tab === "results" && this.appStateStore.search_result_ids.length === 0)
    },
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col items-center justify-center">


    <SearchArea v-if="true" class="flex-none"></SearchArea>

    <div v-if="false"
      class="grid min-h-0 min-w-0 gap-4 overflow-hidden"
      :class="{
        'mx-auto': use_single_column,
        'mr-auto': !use_single_column,
        'grid-cols-1': use_single_column,
        'grid-cols-2': !use_single_column,
        'max-w-4xl': use_single_column,
        'max-w-7xl': !use_single_column,
      }"
      style="grid-auto-rows: minmax(auto, min-content)">

      <!-- left column -->
      <div ref="left_column" class="pointer-events-none flex flex-col overflow-hidden">

        <!-- search card -->
        <!--  -->

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
              Search
            </button>
            <button
              @click="selected_tab = 'chats'"
              :class="{ 'text-blue-500': selected_tab === 'chats' }"
              class="flex-1">
              Questions
            </button>
            <button
              @click="selected_tab = 'collections'; eventBus.emit('collections_tab_is_clicked')"
              :class="{ 'text-blue-500': selected_tab === 'collections' }"
              class="flex-1">
              Collections
            </button>
            <button
              @click="selected_tab = 'datasets'; eventBus.emit('datasets_tab_is_clicked')"
              :class="{ 'text-blue-500': selected_tab === 'datasets' }"
              class="flex-1">
              Datasets
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

              <RangeFilterList></RangeFilterList>

              <div
                v-if="appState.search_result_ids.length !== 0 && appState.cluster_data.length !== 0"
                class="ml-2 mt-1 flex flex-row items-center">
                <span class="mr-2 flex-none text-gray-500">Cluster:</span>
                <div class="flex-1 h-10">
                  <select
                    v-model="appState.selected_cluster_id"
                    class="w-full h-[90%] text-md flex-1 rounded border-transparent text-gray-500 focus:border-blue-500 focus:ring-blue-500">
                    <option :value="null" selected>All</option>
                    <option v-for="cluster in appState.cluster_data" :value="cluster.id" selected>
                      {{ cluster.title }}
                    </option>
                  </select>
                </div>
              </div>

              <ResultList></ResultList>
            </div>

            <!-- ChatList needs v-show instead of v-if to be able to react to show_chat signal -->
            <ChatList v-show="selected_tab === 'chats'"></ChatList>

            <CollectionArea v-if="selected_tab === 'collections'"> </CollectionArea>

            <DatasetsArea v-if="selected_tab === 'datasets'"></DatasetsArea>
          </div>
        </div>
      </div>

      <!-- right column (e.g. for showing box with details for selected result) -->
      <div
        ref="right_column"
        class="pointer-events-none flex flex-col overflow-hidden"
        :class="{'h-screen': !use_single_column}">
        <div
          v-if="appState.selected_document_ds_and_id !== null"
          class="pointer-events-auto flex w-full flex-initial overflow-hidden">
          <ObjectDetailsModal
            :initial_item="appState.get_item_by_ds_and_id(appState.selected_document_ds_and_id)"
            :dataset="appState.datasets[appState.selected_document_ds_and_id[0]]"
            :show_action_buttons="true"></ObjectDetailsModal>
        </div>

        <div v-if="appState.show_loading_bar" class="flex w-full flex-1 flex-col justify-center items-center">
          <div class="flex flex-col p-4 bg-white shadow-xl rounded-xl">
            <span class="self-center font-bold text-gray-400">{{ appState.progress_step_title }}</span>
            <div class="mt-2 h-2.5 w-32 self-center rounded-full bg-gray-400/50">
              <div
                class="h-2.5 rounded-full bg-blue-400"
                :style="{ width: (appState.progress * 100).toFixed(0) + '%' }"></div>
            </div>
          </div>
        </div>

        <div
          v-if="!appState.show_loading_bar && !appState.search_result_ids.length && !appState.map_id"
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

  </div>

</template>

<style scoped>
</style>
