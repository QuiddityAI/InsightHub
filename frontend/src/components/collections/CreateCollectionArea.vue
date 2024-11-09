<script setup>

import { PaperAirplaneIcon, TableCellsIcon } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import Message from 'primevue/message';
import OverlayPanel from 'primevue/overlaypanel';
import InputSwitch from 'primevue/inputswitch';

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
  props: [],
  emits: [],
  data() {
    return {
      settings_template: {
        dataset_id: null,
        mode: 'assisted_search',
        auto_set_filters: true,
        filters: [],
        user_input: '',
        result_language: null,
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
      },
      new_settings: {
        dataset_id: null,
        mode: 'assisted_search',
        auto_set_filters: true,
        filters: [],
        user_input: '',
        result_language: null,
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
      },
      modes: [
        {
          id: 'assisted_search',
          name: 'Assisted Search',
          subtitle: 'Search + Eval',
          help_text: 'Search and evaluate the results',
          query_field_hint: (entity_name) => `Describe what ${entity_name} you want to find`,
          supports_filters: true,
        },
        {
          id: 'classic_search',
          name: 'Classic Search',
          subtitle: 'Just Search',
          help_text: 'Just search, no LLMs',
          query_field_hint: (entity_name) => `Describe what ${entity_name} you want to find`,
          supports_filters: true,
        },
        // {
        //   id: 'auto_select',
        //   name: 'Auto Select',
        //   subtitle: 'curate / high precision search',
        //   help_text: 'Curate the results to select the best candidates',
        //   query_field_hint: (entity_name) => `Describe what ${entity_name} should be selected`,
        //   supports_filters: true,
        // },
        {
          id: 'question',
          name: 'Question',
          subtitle: 'auto select + summary',
          help_text: 'Ask a question and get a summary of the results',
          query_field_hint: (entity_name) => `Your question`,
          supports_filters: true,
        },
        // {
        //   id: 'report',
        //   name: 'Report',
        //   subtitle: 'auto select + long summary',
        //   help_text: 'Get a long summary of the results',
        //   query_field_hint: (entity_name) => `Describe what the report should be about`,
        //   supports_filters: true,
        // },
        // {
        //   id: 'nested_report',
        //   name: 'Multi-Aspect Report',
        //   subtitle: 'multi section + auto select + long summary',
        //   help_text: 'Get a long summary of the results with multiple sections',
        //   query_field_hint: (entity_name) => `Describe the report and the sections`,
        //   supports_filters: true,
        // },
        {
          id: 'overview_map',
          name: 'Overview Map',
          subtitle: 'many candidates + map',
          help_text: 'Get a map of the results',
          query_field_hint: (entity_name) => `Describe what ${entity_name} you want to find`,
          supports_filters: true,
        },
        {
          id: 'empty_collection',
          name: 'Empty Collection',
          subtitle: 'empty collection',
          help_text: 'Create an empty collection',
          query_field_hint: (entity_name) => `Name of the collection`,
          supports_filters: false,
        },
      ],

      example_query_index: 0,
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
      const dataset_languages = this.appStateStore.available_language_filters.map(item => languages.find(lang => lang.code == item[1]))
      const any_language = [{ name: 'any', code: null, flag: '🌍' }]
      return any_language.concat(dataset_languages)
    },
    query_uses_operators_and_meaning() {
      const uses_meaning = ["vector", "hybrid"].includes(this.new_settings.retrieval_mode)
      const operators = [" AND ", " OR ", " NOT "]
      const uses_operators = operators.some((op) => this.new_settings.user_input.includes(op))
      return uses_operators && uses_meaning
    },
    query_includes_other_quotes() {
      const other_quotes = ["'", "`", "´", "‘", "’", "“", "”", "„", "‟", "❛", "❜", "❝", "❞", "＇", "＂"]
      const query = this.new_settings.user_input
      return other_quotes.some((quote) => query.includes(" " + quote) || query.includes(quote + " "))
    },
    using_meaning_for_non_english_search() {
      return this.new_settings.result_language !== "en" && ["vector", "hybrid"].includes(this.new_settings.retrieval_mode)
    },
    example_queries() {
      if (this.new_settings.dataset_id === null) {
        return []
      }
      return this.appStateStore.datasets[this.new_settings.dataset_id]?.advanced_options.example_queries || []
    },
    show_warning_about_missing_meaning_search() {
      const non_keyword = this.new_settings.retrieval_mode !== 'keyword'
      return non_keyword && false  // disable warning for now
    },
    ai_is_available() {
      // show AI features when not logged in as an example, is restricted elsewhere
      return !this.appStateStore.logged_in || this.appStateStore.user.used_ai_credits < this.appStateStore.user.total_ai_credits
    },
    selected_mode() {
      return this.modes.find(mode => mode.id === this.new_settings.mode)
    },
  },
  mounted() {
    this.new_settings = JSON.parse(JSON.stringify(this.settings_template))
    this.new_settings.result_language = this.appStateStore.settings.search.result_language
    // increase example query index every few seconds
    setInterval(() => {
      this.example_query_index = this.example_query_index + 1
    }, 6000)

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
    'appStateStore.settings.search.result_language'(new_val, old_val) {
      this.new_settings.result_language = new_val
    },
    'new_settings.dataset_id'(new_val, old_val) {
      // TODO: the logic to change dataset dependend options should be moved somewhere else, this is just retrofitting
      if (new_val === null && new_val === undefined) return
      this.appStateStore.settings.search.dataset_ids = [new_val]
      this.appStateStore.on_selected_datasets_changed()
    },
  },
  methods: {
    create_collection() {
      const that = this
      if (!this.appStateStore.logged_in) {
        this.eventBus.emit("show_login_dialog", {message: "Login or register to continue searching"})
        return
      }
      if (!this.new_settings.dataset_id) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please select a source dataset', life: 2000 })
        return
      }
      if (!this.new_settings.user_input && !this.new_settings.filters.length) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter a query', life: 2000 })
        return
      }
      this.new_settings.related_organization_id = this.appStateStore.organization_id
      httpClient
        .post("/api/v1/workflows/create_collection", this.new_settings)
        .then(function (response) {
          // put the new collection at the beginning of the list
          const collection = response.data
          that.collectionStore.available_collections.unshift(collection)
          that.appStateStore.last_used_collection_id = collection.id
          that.appStateStore.last_used_collection_class = collection.actual_classes[0].name
          that.collectionStore.open_collection(collection.id, collection.actual_classes[0].name)
        })
    },
    run_example_query(example) {
      this.new_settings.user_input = example.query
      this.new_settings.filters = example.filters || []
      this.new_settings.retrieval_mode = example.search_type
      this.auto_set_filters = example.use_smart_search || true
    },
  },
}
</script>

<template>

  <div class="mt-[200px] w-[650px]">

    <div class="flex flex-col gap-10 bg-white pt-7 pb-10 rounded-lg shadow-md">

      <div class="flex flex-row gap-2 items-center px-7">
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

      <div class="flex flex-row items-center gap-5 pl-7 pr-7 text-gray-500 font-semibold overflow-x-auto">
        <button v-for="mode in modes" @click="new_settings.mode = mode.id"
          class="min-w-[180px] w-[180px] h-[90px] text-md px-3 py-3 bg-gray-100 border-green-300 rounded-xl flex flex-col gap-2 items-center justify-top hover:text-gray-900"
          :class="{
            'border': new_settings.mode == mode.id,
            'bg-green-100': new_settings.mode == mode.id,
          }" v-tooltip.bottom="{ value: mode.help_text, showDelay: 400 }">
          {{ mode.name }}
          <span class="text-xs text-gray-400">{{ mode.subtitle }}</span>
        </button>
      </div>

      <div class="flex flex-col gap-4 px-7">

        <div class="relative flex-none h-10 flex flex-row gap-3 items-center">
          <input type="search" name="search" @keyup.enter="create_collection" v-model="new_settings.user_input"
            autocomplete="off"
            :placeholder="selected_mode.query_field_hint(new_settings.dataset_id ? appState.datasets[new_settings.dataset_id]?.schema.entity_name || '' : 'item')"
            class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
          <div class="" v-if="available_languages.length && !new_settings.auto_set_filters">
            <select v-model="new_settings.result_language" class="w-18 appearance-none ring-0 border-0 bg-transparent"
              v-tooltip.bottom="{ value: 'Language of the query and search results', showDelay: 400 }">
              <option v-for="language in available_languages" :value="language.code">{{ language.flag }}</option>
            </select>
          </div>
          <button v-tooltip.bottom="{ value: 'Submit', showDelay: 400 }"
            class="px-2 h-10 w-32 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
            @click="create_collection">
            Go <PaperAirplaneIcon class="inline h-5 w-5"></PaperAirplaneIcon>
          </button>
        </div>

        <div v-if="!new_settings.auto_set_filters && selected_mode.supports_filters" class="flex flex-row gap-1 items-center">
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
              <AddFilterMenu @close="$refs.add_filter_menu.hide()" :filters="new_settings.filters">
              </AddFilterMenu>
            </OverlayPanel>
          </div>
        </div>

        <Message v-if="show_warning_about_missing_meaning_search" class="" :closable="false">
          Meaning / hybrid search is not yet available for this dataset.
        </Message>

        <!-- <Message v-if="!new_settings.auto_set_filters && using_meaning_for_non_english_search" class="" :closable="false">
          Meaning / hybrid search only works for English queries.
        </Message> -->

        <div v-if="!new_settings.auto_set_filters && query_uses_operators_and_meaning" class="text-xs text-gray-400">
          The operators AND / OR are not supported for 'meaning' and 'hybrid' searches.<br>
          Please use filters and quoted phrases here or switch to 'keyword' search.
        </div>

        <div v-if="!new_settings.auto_set_filters && query_includes_other_quotes" class="text-xs text-gray-400">
          Note: use double quotes instead of single quotes to search for phrases.
        </div>

        <SearchFilterList v-if="!new_settings.auto_set_filters"
          :removable="true"
          :filters="new_settings.filters"></SearchFilterList>

        <div v-if="selected_mode.supports_filters"
          class="ml-1 flex flex-row items-center"
          v-tooltip.top="{ value: ai_is_available ? '' : 'No more AI credits available' }">
          <InputSwitch v-model="new_settings.auto_set_filters" :binary="true" :disabled="!ai_is_available" class="scale-75" />
          <button class="ml-2 text-xs text-gray-500" :disabled="!ai_is_available"
            @click="new_settings.auto_set_filters = !new_settings.auto_set_filters">
            Auto-detect best search strategy and required filters from query
          </button>
        </div>

      </div>

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

</template>

<style scoped></style>
