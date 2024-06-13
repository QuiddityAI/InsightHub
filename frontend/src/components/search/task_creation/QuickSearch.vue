<script setup>
import {
  AdjustmentsHorizontalIcon,
  MinusCircleIcon,
  ClockIcon,
  BookmarkIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftIcon,
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Listbox from 'primevue/listbox';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';
import InputSwitch from 'primevue/inputswitch';
import OverlayPanel from "primevue/overlaypanel";
import Checkbox from "primevue/checkbox";

import AddFilterMenu from "../AddFilterMenu.vue";
import SearchFilterList from "../SearchFilterList.vue";

import { httpClient, djangoClient } from "../../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../../stores/app_state_store"
import { useMapStateStore } from "../../../stores/map_state_store"

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
      use_smart_search: true,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    grouped_available_datasets() {
      const grouped = {}
      for (const dataset of Object.values(this.appStateStore.datasets)) {
        const group = dataset.is_public ? "Public Sources" : "Your Files"
        if (!grouped[group]) {
          grouped[group] = { label: group, items: []}
        }
        grouped[group].items.push(dataset)
      }
      const preferred_order = ["Semantic Scholar", "OpenAlex", "OpenLibrary"]
      for (const dataset_name of preferred_order.slice().reverse()) {
        if (grouped["Public Sources"]?.items.find(item => item.name === dataset_name)) {
          const element = grouped["Public Sources"].items.find(item => item.name === dataset_name)
          grouped["Public Sources"].items = grouped["Public Sources"].items.filter(item => item.name !== dataset_name)
          grouped["Public Sources"].items.unshift(element)
        }
      }
      return [grouped["Public Sources"], grouped["Your Files"]]
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
  <div class="flex flex-col">
    <div class="flex flex-row gap-10">
      <div class="w-[250px] flex flex-col">
        <Listbox multiple metaKeySelection
          v-model="appState.settings.search.dataset_ids"
          :options="grouped_available_datasets"
          optionGroupLabel="label"
          optionGroupChildren="items"
          optionLabel="name"
          optionValue="id"
          class="w-full"
          listStyle="height:225px">
          <template #option="slotProps">
              <div class="flex flex-col">
                  <div class="text-sm">{{ slotProps.option.name }}</div>
                  <!-- inline style instead of tailwind necessary here -->
                  <div class="pl-1 text-xs text-gray-500" style="text-wrap: wrap;">{{ slotProps.option.short_description }}</div>
              </div>
          </template>
        </Listbox>
        <p v-if="appState.settings.search.dataset_ids.length >= 2" class="text-gray-500 text-sm mt-2 ml-2">
          {{ appState.settings.search.dataset_ids.length }} sources selected</p>
        <p v-if="appState.settings.search.dataset_ids.length == 1" class="text-gray-400 text-xs mt-2 ml-2">
          Select multiple by holding Ctrl</p>
        <Message v-if="appState.settings.search.dataset_ids.length === 0" class="text-gray-500 text-sm mt-2">
          Select at least one source</Message>
      </div>


      <div class="flex-1 mr-4 flex flex-col justify-center">
        <div class="flex flex-row">
          <div class="flex-1 h-9 flex flex-row items-center">
            <input
              type="search"
              name="search"
              @keyup.enter="use_smart_search ? run_smart_search() : appState.request_search_results()"
              v-model="appState.settings.search.all_field_query"
              :placeholder="`Describe what ${appState.settings.search.dataset_ids.length ? appState.datasets[appState.settings.search.dataset_ids[0]]?.schema.entity_name || '' : ''} you want to find`"
              class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
          </div>
          <button v-if="!processing_smart_search"
            v-tooltip.bottom="{value: 'Submit', showDelay: 400}"
            class="ml-2 px-2 h-9 w-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
            @click="run_smart_search()">
            <PaperAirplaneIcon class="h-5 w-5"></PaperAirplaneIcon>
          </button>
          <ProgressSpinner v-if="processing_smart_search" class="ml-1 w-5 h-5"></ProgressSpinner>
        </div>

        <div v-if="!use_smart_search" class="mt-5 ml-0 flex flex-row gap-1 items-center">
          <div class="flex flex-row items-center gap-0 h-6">
            <button class="border border-gray-300 rounded-l-md px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
              @click="appState.settings.search.search_algorithm = 'keyword'"
              v-tooltip="{ value: 'Use this to find specific words.\nSupports operators like AND / OR / NOT.', showDelay: 400 }"
              :class="{'text-blue-500': appState.settings.search.search_algorithm === 'keyword', 'text-gray-400': appState.settings.search.search_algorithm != 'keyword'}">
              Keyword
            </button>
            <button class="border border-gray-300  rounded-none px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
              @click="appState.settings.search.search_algorithm = 'vector'"
              v-tooltip="{ value: 'Use this to search for broader topics or information\nthat can be described in many different ways.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
              :class="{'text-blue-500': appState.settings.search.search_algorithm === 'vector', 'text-gray-400': appState.settings.search.search_algorithm != 'vector'}">
              Meaning
            </button>
            <button class="border border-gray-300 rounded-r-md  px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
              @click="appState.settings.search.search_algorithm = 'hybrid'"
              v-tooltip="{ value: 'Combines keyword and meaning search.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
              :class="{'text-blue-500': appState.settings.search.search_algorithm === 'hybrid', 'text-gray-400': appState.settings.search.search_algorithm != 'hybrid'}">
              Both
            </button>
          </div>
          <div class="flex-1"></div>
          <div class="flex flex-row items-center gap-0 h-6">
            <button class="border border-gray-300 rounded-md  px-1 text-sm font-['Lexend'] font-normal text-gray-400 hover:bg-gray-100"
              v-tooltip.bottom="{ value: 'Add filters and change search options', showDelay: 400 }"
              @click="(event) => { $refs.add_filter_menu.toggle(event) }">
              + Filter / Option
            </button>
            <OverlayPanel ref="add_filter_menu">
              <AddFilterMenu @close="$refs.add_filter_menu.hide()">
              </AddFilterMenu>
            </OverlayPanel>
          </div>
        </div>

        <SearchFilterList v-if="!use_smart_search"></SearchFilterList>

        <div class="mt-5 ml-1 mb-5 flex flex-row items-center">
          <Checkbox v-model="use_smart_search" class="" :binary="true" />
          <span class="ml-2 text-xs text-gray-500">
            Auto-detect best search strategy and required filters from query
          </span>
        </div>

      </div>

    </div>

    <div v-if="!selected_task_type" class="mt-4 flex flex-row items-end">
      <img src="assets/up_left_arrow.svg" class="ml-12 mr-4 pb-1 w-8" />
      <span class="text-gray-500 italic">Want to search your own files? Upload them at the top.</span>
    </div>
  </div>

</template>

<style scoped>
</style>
