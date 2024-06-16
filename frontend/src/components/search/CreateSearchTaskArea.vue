<script setup>
import {
} from "@heroicons/vue/24/outline"

import SearchHistoryDialog from "../history/SearchHistoryDialog.vue";
import StoredMapsDialog from "../history/StoredMapsDialog.vue";
import QuickSearch from "./task_creation/QuickSearch.vue";
import CustomSearch from "./task_creation/CustomSearch.vue";
import QuestionTask from "./task_creation/QuestionTask.vue";
import HighPrecisionSearch from "./task_creation/HighPrecisionSearch.vue";
import TopicOverview from "./task_creation/TopicOverview.vue";
import SimilaritySearch from "./task_creation/SimilaritySearch.vue";

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useToast } from 'primevue/usetoast';
const toast = useToast()

const appState = useAppStateStore()
const _window = window
const _history = history
</script>

<script>
// combined: all fields in "default search fields" with same query (+negatives), as OR, reciprocal rank fusion

// fulltext: opensearch, all text fields, opensearch dql language for negatives
//    - "must": add to AND set
// description_vector: vector search, knee threshold function, minus operator for negatives
//    - generator -> embedding space -> other generators -> set of types -> fields
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// image_vector: vector search, knee threshold function, minus operator for negatives
//    - "more / less results slider": change knee algo setting
//    - "must": add to AND set
// filter out items that are not in AND sets, reciprocal rank fusion

// auto generated filter criteria set (later, maybe simple ones for now)

// external input: combined (pos, neg, text),
//     separate fields (pos, neg with text or image (if supported)),
// similar to item (list of fields, e.g. descr. or image, fields are OR),
// matching to classifier (classifier id),
// cluster id of map id

export default {
  inject: ["eventBus"],
  emits: [],
  data() {
    return {
      available_task_types: [
        { task_type: 'quick_search', title: 'Quick Search', tooltip: 'Quick and easy search, with the results presented in a list and visually on a map' },
        { task_type: 'topic_overview', title: 'Topic Overview', tooltip: "Like 'Quick Search', but provides a more advanced structure of the map together with summaries of each subarea" },
        { task_type: 'question', title: 'Question', tooltip: "Ask a question and get a direct answer, including citations" },
        { task_type: 'similarity', title: 'Find by Similarity', tooltip: "Upload a file and find similar items" },
        { task_type: 'high_precision_search', title: 'High Precision Search', advanced: true, tooltip: "Slow, but evaluates each result using AI to only return truly relevant items. Can be used to exhaustively find all relevant items in a database." },
        { task_type: 'custom_search', title: 'Custom Search', advanced: true, tooltip: "Allows you to configure all parameters of the search yourself" },
      ],
      show_advanced_options: false,

    }
  },
  mounted() {
    const that = this
    this.eventBus.on("show_results_tab", () => {
      that.use_smart_search = false
    })
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  watch: {
  },
  methods: {
    open_search_history_dialog() {
      this.$dialog.open(SearchHistoryDialog, {props: {header: "Search History", modal: true}});
    },
    open_stored_maps_dialog() {
      this.$dialog.open(StoredMapsDialog, {props: {header: "Stored Maps", modal: true}});
    },
  },
}
</script>

<template>
  <div class="w-full max-w-[900px]">
    <div class="px-5 md:px-12 pt-10 pb-10 pointer-events-auto rounded-xl bg-white shadow-lg">

      <!-- Task Type Selection -->
      <p v-if="!appState.settings.search.task_type" class="mb-6 text-lg text-gray-500 font-normal">
        Select what you want to do:</p>
      <div class="flex flex-row items-center justify-between gap-6 text-gray-500 font-semibold">
        <button v-for="task_type in available_task_types.filter(task_type => !task_type.advanced)"
          class="text-md bg-gray-100 rounded-md px-3 py-1 hover:text-blue-500"
          :class="{ 'text-blue-500': appState.settings.search.task_type === task_type.task_type }"
          v-tooltip.top="{ value: task_type.tooltip, showDelay: 400 }"
          @click="appState.settings.search.task_type === task_type.task_type ? appState.settings.search.task_type = null : appState.settings.search.task_type = task_type.task_type">
          {{ task_type.title }}
        </button>
        <button @click="show_advanced_options = !show_advanced_options"
          class="text-md font-normal bg-gray-100 rounded-md px-3 py-1 hover:text-blue-500"
          :class="{ 'text-blue-500': show_advanced_options }">
          More
        </button>
      </div>
      <div v-if="show_advanced_options" class="mt-3 flex flex-row items-center justify-left gap-6 text-gray-500 font-semibold">
        <button v-for="task_type in available_task_types.filter(task_type => task_type.advanced)"
          class="text-md bg-gray-100 rounded-md px-3 py-1 hover:text-blue-500"
          :class="{ 'text-blue-500': appState.settings.search.task_type === task_type.task_type }"
          v-tooltip.top="{ value: task_type.tooltip, showDelay: 400 }"
          @click="appState.settings.search.task_type === task_type.task_type ? appState.settings.search.task_type = null : appState.settings.search.task_type = task_type.task_type">
          {{ task_type.title }}
        </button>
      </div>
      <div v-if="!appState.settings.search.task_type && !show_advanced_options" class="mt-4 flex flex-row items-end">
        <img src="assets/up_left_arrow.svg" class="ml-12 mr-4 pb-1 w-8" />
        <span class="text-gray-500 italic">Start here if your are new!</span>
      </div>

      <QuickSearch v-if="appState.settings.search.task_type === 'quick_search'" class="mt-10"></QuickSearch>
      <TopicOverview v-if="appState.settings.search.task_type === 'topic_overview'" class="mt-10"></TopicOverview>
      <QuestionTask v-if="appState.settings.search.task_type === 'question'" class="mt-10"></QuestionTask>
      <SimilaritySearch v-if="appState.settings.search.task_type === 'similarity'" class="mt-10"></SimilaritySearch>
      <HighPrecisionSearch v-if="appState.settings.search.task_type === 'high_precision_search'" class="mt-10"></HighPrecisionSearch>
      <CustomSearch v-if="appState.settings.search.task_type === 'custom_search'" class="mt-10"></CustomSearch>

    </div>

    <div v-if="!appState.settings.search.task_type && appState.logged_in && appState.search_history.length"
      class="max-w-[900px] mt-10 px-5 md:px-12 pt-6 pb-6 pointer-events-auto rounded-xl bg-white shadow-sm">
      <div class="flex flex-row gap-4 items-center text-gray-400">
        <span class="">Continue where you left off:</span>
        <button v-for="history_item in appState.search_history.slice().reverse().slice(0, 2)"
          class="bg-gray-100 rounded-md px-2 py-1 text-sm hover:bg-blue-100/50"
          v-tooltip.bottom="{ value: 'Run this search again', showDelay: 400 }"
          @click="appState.run_search_from_history(history_item)">
          <span class="font-medium" v-html="history_item.display_name"></span>
        </button>
        <button
          class="text-sm hover:text-blue-500"
          @click="open_search_history_dialog()">
          <span class="font-medium italic">Show all</span>
        </button>
      </div>
    </div>
  </div>
</template>
