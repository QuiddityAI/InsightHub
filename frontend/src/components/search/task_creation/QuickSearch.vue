<script setup>
import {
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Listbox from 'primevue/listbox';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';
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
      processing_smart_search: false,
      example_query_index: 0,
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
    query_uses_operators_and_meaning() {
      const uses_meaning = ["vector", "hybrid"].includes(this.appStateStore.settings.search.search_algorithm)
      const operators = [" AND ", " OR ", " NOT "]
      const uses_operators = operators.some((op) => this.appStateStore.settings.search.all_field_query.includes(op))
      return uses_operators && uses_meaning
    },
    query_includes_other_quotes() {
      const other_quotes = ["'", "`", "´", "‘", "’", "“", "”", "„", "‟", "❛", "❜", "❝", "❞", "＇", "＂"]
      const query = this.appStateStore.settings.search.all_field_query
      return other_quotes.some((quote) => query.includes(" " + quote) || query.includes(quote + " "))
    },
    example_queries() {
      if (this.appStateStore.settings.search.dataset_ids.length === 0) {
        return []
      }
      return this.appStateStore.datasets[this.appStateStore.settings.search.dataset_ids[0]]?.advanced_options.example_queries || []
    },
    show_warning_about_missing_meaning_search() {
      const non_keyword = this.appStateStore.settings.search.search_algorithm !== 'keyword'
      const is_s2_or_oa = this.appStateStore.settings.search.dataset_ids.filter(id => ['OpenAlex', 'Semantic Scholar'].includes(this.appStateStore.datasets[id].name)).length > 0
      return non_keyword && is_s2_or_oa
    }
  },
  mounted() {
    // increase example query index every few seconds
    setInterval(() => {
      this.example_query_index = this.example_query_index + 1
    }, 6000)
    this.eventBus.on('edit_search_parameters', () => {
      this.use_smart_search = false
    })
  },
  watch: {
  },
  methods: {
    run_smart_search() {
      if (this.processing_smart_search) return
      if (!this.appStateStore.settings.search.all_field_query) {
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Please enter a query', life: 5000})
        return
      }
      if (this.appStateStore.settings.search.dataset_ids.length === 0) {
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Please select at least one source', life: 5000})
        return
      }
      if (!this.appStateStore.check_if_search_is_allowed({use_credit: false})) return

      djangoClient.post(`/org/data_map/convert_smart_query_to_parameters`, {
        user_id: this.appStateStore.user.id,
        query: this.appStateStore.settings.search.all_field_query,
      }).then((response) => {
        this.processing_smart_search = false
        const search_parameters = response.data.search_parameters
        this.appStateStore.settings.search.all_field_query = search_parameters.query
        for (const filter of search_parameters.filters) {
          filter.dataset_id = this.appStateStore.settings.search.dataset_ids[0]
        }
        this.appStateStore.settings.search.filters = search_parameters.filters || []
        if (search_parameters.search_type == "meaning") {
          search_parameters.search_type = "vector"
        }
        this.appStateStore.settings.search.search_algorithm = search_parameters.search_type
        // disable smart search because when editing the search params, it should not be re-run
        this.use_smart_search = false
        this.appStateStore.request_search_results()
      }).catch((error) => {
        console.log(error)
        this.processing_smart_search = false
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Smart search failed', life: 5000})
      })
      this.processing_smart_search = true
    },
    run_example_query(example) {
      this.appStateStore.settings.search.all_field_query = example.query
      this.appStateStore.settings.search.filters = example.filters || []
      this.appStateStore.settings.search.search_algorithm = example.search_type
      this.use_smart_search = example.use_smart_search || true
    },
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
          @change="appState.on_selected_datasets_changed"
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
              autocomplete="off"
              :disabled="processing_smart_search"
              :placeholder="`Describe what ${appState.settings.search.dataset_ids.length ? appState.datasets[appState.settings.search.dataset_ids[0]]?.schema.entity_name || '' : ''} you want to find`"
              class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
          </div>
          <button v-if="!processing_smart_search"
            v-tooltip.bottom="{value: 'Submit', showDelay: 400}"
            class="ml-2 px-2 h-9 w-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
            @click="use_smart_search ? run_smart_search() : appState.request_search_results()">
            <PaperAirplaneIcon class="h-5 w-5"></PaperAirplaneIcon>
          </button>
          <div class="flex items-center justify-center">
            <ProgressSpinner v-if="processing_smart_search" class="ml-1 w-5 h-5"></ProgressSpinner>
          </div>
        </div>

        <div v-if="!use_smart_search" class="mt-3 ml-0 flex flex-row gap-1 items-center">
          <div class="flex flex-row items-center gap-0 h-6">
            <button class="border border-gray-300 rounded-l-md px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
              @click="appState.settings.search.search_algorithm = 'keyword'"
              v-tooltip="{ value: 'Use this to find specific words.\nSupports operators like AND / OR / NOT.', showDelay: 400 }"
              :class="{'text-blue-500': appState.settings.search.search_algorithm === 'keyword', 'text-gray-400': appState.settings.search.search_algorithm != 'keyword'}">
              Keywords
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

        <Message v-if="show_warning_about_missing_meaning_search" class="mt-3" :closable="false">
          Meaning / hybrid search is not yet available for this dataset. It is coming mid July. Try it using uploaded files or OpenLibrary for now.
        </Message>

        <div v-if="!use_smart_search && query_uses_operators_and_meaning" class="mt-3 text-xs text-gray-400">
          The operators AND / OR are not supported for 'meaning' and 'hybrid' searches.<br>
          Please use filters and quoted phrases here or switch to 'keyword' search.
        </div>

        <div v-if="!use_smart_search && query_includes_other_quotes" class="mt-3 text-xs text-gray-400">
          Note: use double quotes instead of single quotes to search for phrases.
        </div>

        <SearchFilterList v-if="!use_smart_search"></SearchFilterList>

        <div class="mt-5 ml-1 mb-5 flex flex-row items-center">
          <Checkbox v-model="use_smart_search" class="" :binary="true" />
          <button class="ml-2 text-xs text-gray-500"
            @click="use_smart_search = !use_smart_search">
            Auto-detect best search strategy and required filters from query
          </button>
        </div>

        <div class="relative">
          <div v-if="example_queries.length" class="absolute top-4 text-sm text-gray-400">
            Try: <button class="underline hover:text-blue-500"
              @click="run_example_query(example_queries[example_query_index % example_queries.length])">
              "{{ example_queries[example_query_index % example_queries.length].query }}"
            </button>
          </div>
        </div>

      </div>

    </div>

    <div class="mt-4 flex flex-row items-end">
      <img src="/assets/up_left_arrow.svg" class="ml-12 mr-4 pb-1 w-8" />
      <span class="text-gray-500 italic">Want to search your own files? Upload them at the top.</span>
    </div>
  </div>

</template>

<style scoped>
</style>
