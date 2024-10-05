<script setup>

import { PaperAirplaneIcon } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import Message from 'primevue/message';
import Checkbox from 'primevue/checkbox';
import OverlayPanel from 'primevue/overlaypanel';

import SearchFilterList from "../search/SearchFilterList.vue"
import AddFilterMenu from "../search/AddFilterMenu.vue"

import { httpClient, djangoClient } from "../../api/httpClient"
import { languages } from "../../utils/utils"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["collection", "collection_class"],
  emits: ["close"],
  data() {
    return {
      settings_template: {
        dataset_id: null,
        auto_set_filters: true,
        query: '',
        result_language: 'en',
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
      },
      new_settings: {
        dataset_id: null,
        auto_set_filters: true,
        query: '',
        result_language: 'en',
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
      },
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    grouped_available_datasets() {
      const grouped = {}
      for (const dataset of Object.values(this.appStateStore.datasets)) {
        const group = dataset.is_public ? "Public Sources" : "Your Files"
        if (!grouped[group]) {
          grouped[group] = { label: group, items: [] }
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
      const groups = []
      if (grouped["Public Sources"]) {
        groups.push(grouped["Public Sources"])
      }
      if (grouped["Your Files"]) {
        groups.push(grouped["Your Files"])
      }
      return groups
    },
    available_languages() {
      return this.appStateStore.available_language_filters.map(item => languages.find(lang => lang.code == item[1]))
    },
    query_uses_operators_and_meaning() {
      const uses_meaning = ["vector", "hybrid"].includes(this.new_settings.retrieval_mode)
      const operators = [" AND ", " OR ", " NOT "]
      const uses_operators = operators.some((op) => this.new_settings.query.includes(op))
      return uses_operators && uses_meaning
    },
    query_includes_other_quotes() {
      const other_quotes = ["'", "`", "´", "‘", "’", "“", "”", "„", "‟", "❛", "❜", "❝", "❞", "＇", "＂"]
      const query = this.new_settings.query
      return other_quotes.some((quote) => query.includes(" " + quote) || query.includes(quote + " "))
    },
    using_meaning_for_non_english_search() {
      return this.new_settings.result_language !== "en" && ["vector", "hybrid"].includes(this.new_settings.retrieval_mode)
    },
    show_warning_about_missing_meaning_search() {
      const non_keyword = this.new_settings.retrieval_mode !== 'keyword'
      return non_keyword && false  // disable warning for now
    },
    ai_is_available() {
      // show AI features when not logged in as an example, is restricted elsewhere
      return !this.appStateStore.logged_in || this.appStateStore.user.used_ai_credits < this.appStateStore.user.total_ai_credits
    },
  },
  mounted() {
    this.new_settings = JSON.parse(JSON.stringify(this.collectionStore.collection.last_search_task || this.settings_template))

    this.new_settings.ranking_settings = this.appStateStore.settings.search.ranking_settings
    this.new_settings.dataset_id = this.appStateStore.settings.search.dataset_ids.length ? this.appStateStore.settings.search.dataset_ids[0] : null
    this.eventBus.on("datasets_are_loaded", () => {
      this.new_settings.dataset_id = this.appStateStore.settings.search.dataset_ids.length ? this.appStateStore.settings.search.dataset_ids[0] : null
    })
  },
  watch: {
    'appStateStore.settings.search.ranking_settings'(new_val, old_val) {
      // TODO: change this?
      this.new_settings.ranking_settings = new_val
    },
  },
  methods: {
    run_search_task() {
      const that = this
      if (!this.new_settings.dataset_id) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please select a source dataset', life: 2000 })
        return
      }
      if (!this.new_settings.query) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter a query', life: 2000 })
        return
      }
      this.new_settings.related_organization_id = this.appStateStore.organization_id
      const body = {
        search_task: this.new_settings,
        collection_id: this.collectionStore.collection_id,
        class_name: this.collectionStore.class_name
      }
      httpClient
        .post("/api/v1/search/run_search_task", body)
        .then(function (response) {
          that.collectionStore.update_collection(() => {
            that.$emit("close")
          })
        })
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-3">

    <div class="flex flex-row gap-2 items-center">
      <div class="flex-none min-w-0">
        <Dropdown v-model="new_settings.dataset_id" :options="grouped_available_datasets" optionLabel="name"
          optionGroupLabel="label" optionGroupChildren="items" optionValue="id" placeholder="Select Source..."
          class="w-full h-full mr-4 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
          <template #option="slotProps">
            <div class="flex flex-col">
              <div class="text-sm">{{ slotProps.option.name }}</div>
              <!-- inline style instead of tailwind necessary here -->
              <div class="pl-1 text-xs text-gray-500" style="text-wrap: wrap;">{{ slotProps.option.short_description }}
              </div>
            </div>
          </template>
        </Dropdown>
      </div>
    </div>

    <div class="flex flex-col gap-3">

      <div class="relative flex-1 h-9 flex flex-row gap-3 items-center">
        <input type="search" name="search" @keyup.enter="run_search_task" v-model="new_settings.query"
          autocomplete="off"
          :placeholder="`Search...`"
          class="w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
        <div class="" v-if="available_languages.length && !new_settings.auto_set_filters">
          <select v-model="new_settings.result_language" class="w-18 appearance-none ring-0 border-0 bg-transparent"
            v-tooltip.bottom="{ value: 'Language of the query and search results', showDelay: 400 }">
            <option v-for="language in available_languages" :value="language.code">{{ language.flag }}</option>
          </select>
        </div>
        <button v-tooltip.bottom="{ value: 'Submit', showDelay: 400 }"
          class="px-2 h-9 w-60 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
          @click="run_search_task">
          Go <PaperAirplaneIcon class="inline h-5 w-5"></PaperAirplaneIcon>
        </button>
      </div>

      <div v-if="!new_settings.auto_set_filters" class="flex flex-row gap-1 items-center">
        <div class="flex flex-row items-center gap-0 h-6">
          <button class="border border-gray-300 rounded-l-md px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
            @click="new_settings.retrieval_mode = 'keyword'"
            v-tooltip="{ value: 'Use this to find specific words.\nSupports operators like AND / OR / NOT.', showDelay: 400 }"
            :class="{ 'text-blue-500': new_settings.retrieval_mode === 'keyword', 'text-gray-400': new_settings.retrieval_mode != 'keyword' }">
            Keywords
          </button>
          <button
            class="border border-gray-300  rounded-none px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
            @click="new_settings.retrieval_mode = 'vector'"
            v-tooltip="{ value: 'Use this to search for broader topics or information\nthat can be described in many different ways.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
            :class="{ 'text-blue-500': new_settings.retrieval_mode === 'vector', 'text-gray-400': new_settings.retrieval_mode != 'vector' }">
            Meaning
          </button>
          <button
            class="border border-gray-300 rounded-r-md  px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
            @click="new_settings.retrieval_mode = 'hybrid'"
            v-tooltip="{ value: 'Combines keyword and meaning search.\n\nNote: this might return almost all documents, but sorted\nso that the most relevant ones are at the top.\nOnly supports quoted phrases, not the AND / OR / NOT operators.', showDelay: 400 }"
            :class="{ 'text-blue-500': new_settings.retrieval_mode === 'hybrid', 'text-gray-400': new_settings.retrieval_mode != 'hybrid' }">
            Both
          </button>
        </div>
        <div class="flex-1"></div>
        <select v-model="new_settings.ranking_settings"
          v-if="appState.available_ranking_options.length > 1 && new_settings.retrieval_mode === 'keyword'"
          class="border border-gray-300 rounded-md text-sm text-gray-400 font-['Lexend'] font-normal pl-2 pr-8 py-0"
          v-tooltip.bottom="{ value: new_settings.ranking_settings?.tooltip, showDelay: 400 }">
          <option v-for="ranking_settings in appState.available_ranking_options" :value="ranking_settings">
            {{ ranking_settings.title }}
          </option>
        </select>
        <div class="flex-1"></div>
        <div class="flex flex-row items-center gap-0 h-6">
          <button
            class="border border-gray-300 rounded-md  px-1 text-sm font-['Lexend'] font-normal text-gray-400 hover:bg-gray-100"
            v-tooltip.bottom="{ value: 'Add filters and change search options', showDelay: 400 }"
            @click="(event) => { $refs.add_filter_menu.toggle(event) }">
            + Filter
          </button>
          <OverlayPanel ref="add_filter_menu">
            <AddFilterMenu @close="$refs.add_filter_menu.hide()">
            </AddFilterMenu>
          </OverlayPanel>
        </div>
      </div>

      <Message v-if="show_warning_about_missing_meaning_search" class="" :closable="false">
        Meaning / hybrid search is not yet available for this dataset.
      </Message>

      <Message v-if="!new_settings.auto_set_filters && using_meaning_for_non_english_search" class="" :closable="false">
        Meaning / hybrid search only works for English queries.
      </Message>

      <div v-if="!new_settings.auto_set_filters && query_uses_operators_and_meaning" class="text-xs text-gray-400">
        The operators AND / OR are not supported for 'meaning' and 'hybrid' searches.<br>
        Please use filters and quoted phrases here or switch to 'keyword' search.
      </div>

      <div v-if="!new_settings.auto_set_filters && query_includes_other_quotes" class="text-xs text-gray-400">
        Note: use double quotes instead of single quotes to search for phrases.
      </div>

      <SearchFilterList v-if="!new_settings.auto_set_filters"></SearchFilterList>

      <div
        class="ml-1 mb-5 flex flex-row items-center"
        v-tooltip.top="{ value: ai_is_available ? '' : 'No more AI credits available' }">
        <Checkbox v-model="new_settings.auto_set_filters" class="" :binary="true" :disabled="!ai_is_available" />
        <button class="ml-2 text-xs text-gray-500" :disabled="!ai_is_available"
          @click="new_settings.auto_set_filters = !new_settings.auto_set_filters">
          Auto-detect best search strategy and required filters from query
        </button>
      </div>

    </div>

  </div>

</template>

<style scoped>
</style>
