<script setup>

import {
  PaperAirplaneIcon,
  ChevronLeftIcon,
  InformationCircleIcon,
 } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import Message from 'primevue/message';
import OverlayPanel from 'primevue/overlaypanel';
import InputSwitch from 'primevue/inputswitch';

import SearchFilterList from "../search/SearchFilterList.vue"
import AddFilterMenu from "../search/AddFilterMenu.vue"
import ToolIntroBox from "../general/ToolIntroBox.vue";

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

const capitalizeFirstLetter = (val) => {
    return String(val).charAt(0).toUpperCase() + String(val).slice(1);
}

export default {
  inject: ["eventBus"],
  props: [],
  emits: [],
  data() {
    return {
      container_height: 'auto',
      settings_template: {
        dataset_id: null,
        workflow_id: null,
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
        workflow_id: null,
        auto_set_filters: true,
        filters: [],
        user_input: '',
        result_language: null,
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
      },
      workflows: [],

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
    selected_workflow() {
      return this.workflows.find(workflow => workflow.workflow_id === this.new_settings.workflow_id)
    },
    entity_name_singular() {
      const schema = this.new_settings.dataset_id ? this.appStateStore.datasets[this.new_settings.dataset_id]?.schema : null
      return schema ? schema.translated_entity_name.singular[this.language] || schema.entity_name : 'item'
    },
    entity_name_plural() {
      const schema = this.new_settings.dataset_id ? this.appStateStore.datasets[this.new_settings.dataset_id]?.schema : null
      return schema ? schema.translated_entity_name.plural[this.language] || schema.entity_name_plural : 'items'
    },
    language() {
      return navigator.language.split('-')[0]
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
    this.eventBus.on("datasets_are_loaded", this.on_datasets_loaded)
    // watch this.$refs.container?.scrollHeight and set container_height:
    const container = this.$refs.container
    if (container) {
      const observer = new ResizeObserver((entries) => {
        for (let entry of entries) {
          this.container_height = (entry.contentRect.height + 30) + 'px'
        }
      })
      observer.observe(container)
    }
  },
  unmounted() {
    this.eventBus.off("datasets_are_loaded", this.on_datasets_loaded)
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
      this.get_available_workflows()
    },
  },
  methods: {
    on_datasets_loaded() {
      this.new_settings.dataset_id = this.appStateStore.settings.search.dataset_ids.length ? this.appStateStore.settings.search.dataset_ids[0] : null
      this.get_available_workflows()
    },
    get_available_workflows() {
      const body = {
        dataset_id: this.new_settings.dataset_id,
      }
      httpClient
        .post("/api/v1/workflows/get_available_workflows", body)
        .then((response) => {
          this.workflows = response.data
        })
    },
    select_workflow(workflow) {
      if (workflow.availability === 'in_development') {
        this.$toast.add({ severity: 'warn', summary: 'Coming Soon', detail: 'This feature is not yet available', life: 3000 })
        return
      }
      this.new_settings.workflow_id = workflow.workflow_id
    },
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
      const needs_query = this.selected_workflow.needs_user_input
      if (!this.new_settings.user_input && !this.new_settings.filters.length && needs_query) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter a query', life: 2000 })
        return
      }
      this.new_settings.related_organization_id = this.appStateStore.organization_id
      httpClient
        .post("/api/v1/workflows/create_collection", this.new_settings)
        .then((response) => {
          // put the new collection at the beginning of the list
          const collection = response.data
          that.collectionStore.available_collections.unshift(collection)
          that.appStateStore.last_used_collection_id = collection.id
          that.appStateStore.last_used_collection_class = collection.actual_classes[0].name
          that.collectionStore.open_collection(collection.id, collection.actual_classes[0].name)
          this.eventBus.emit("collection_items_changed_on_server")
        })
    },
    run_example_query(example) {
      this.new_settings.user_input = example.query
      this.new_settings.filters = example.filters || []
      this.new_settings.retrieval_mode = example.search_type
      this.auto_set_filters = example.use_smart_search || true
    },
    fill_placeholders(str, uppercase=false) {
      if (!str) return ''
      const singular = uppercase ? capitalizeFirstLetter(this.entity_name_singular) : this.entity_name_singular
      const plural = uppercase ? capitalizeFirstLetter(this.entity_name_plural) : this.entity_name_plural
      return str.replace('<entity_name_singular>', singular).replace('<entity_name_plural>', plural)
    },
  },
}
</script>

<template>

  <div class="mt-[200px] w-[650px] flex flex-col gap-5 pb-10">

    <!-- create collection box -->
    <div class="bg-white rounded-lg shadow-md transition-[height] duration-200 ease-out overflow-hidden min-h-0 max-h-none"
    :style="{ height: container_height }">
      <div class="flex flex-col gap-8 pt-1 pb-10" ref="container">

        <div class="flex flex-row gap-2 items-center justify-between px-3">
          <div class="flex-none w-10">
            <button v-if="selected_workflow != null" @click="new_settings.workflow_id = null"
              class="flex-none w-10 rounded-md hover:bg-blue-100/50 text-gray-400">
              <ChevronLeftIcon class="inline h-5 w-5"></ChevronLeftIcon>
            </button>
          </div>

          <div class="flex-none min-w-0">
            <Dropdown v-model="new_settings.dataset_id" :options="grouped_available_datasets" optionLabel="name"
              optionGroupLabel="label" optionGroupChildren="items" optionValue="id" placeholder="Select Source..."
              @change="new_settings.workflow_id = null"
              class="h-full border-none text-sm font-medium" id="datasetdropdown"> <!-- see CSS below for text color -->
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
          <div class="flex-none w-10"></div>
        </div>

        <div v-if="selected_workflow == null" class="flex flex-col gap-5 items-start">

          <h1 class="pl-11 text-3xl font-bold bg-gradient-to-r from-black via-fuchsia-700 to-blue-700 text-transparent bg-clip-text">
            {{ $t('CreateCollectionArea.what-do-you-want-to-do') }}
          </h1>

          <div class="flex flex-row w-full items-center gap-5 pl-10 pr-7 py-4 overflow-x-auto">
            <button v-for="workflow in workflows" @click="select_workflow(workflow)"
              class="min-w-[170px] w-[170px] h-[93px] px-3 py-3 bg-gray-100 shadow-md rounded-xl flex flex-col gap-0 items-start justify-start group"
              :class="{
                'border': new_settings.workflow_id == workflow.workflow_id,
                'bg-green-100': new_settings.workflow_id == workflow.workflow_id,
              }" v-tooltip.bottom="{ value: fill_placeholders(workflow.help_text[language] || workflow.help_text.en) + (workflow.availability === 'in_development' ? ' (coming soon)' : ''), showDelay: 600 }">
              <div class="text-left text-sm font-bold text-gray-500" v-html="workflow.name1[language] || workflow.name1.en"></div>
              <div class="text-left font-bold transition-colors"
                :class="{ 'group-hover:text-gray-800': workflow.availability !== 'in_development',
                  'text-gray-600': workflow.availability !== 'in_development',
                  'group-hover:text-gray-600': workflow.availability === 'in_development',
                  'text-gray-500': workflow.availability === 'in_development', }"
                v-html="fill_placeholders(workflow.name2[language] || workflow.name2.en, true) + (workflow.availability === 'in_development' ? ' (in dev.)' : '')"></div>
            </button>
          </div>

        </div>

        <div v-if="selected_workflow != null" class="flex flex-col gap-4 px-7">

          <div class="text-xl font-bold text-gray-800">
            {{ selected_workflow.name1[language] || selected_workflow.name1.en }}
            <span class="bg-gradient-to-r from-fuchsia-900 via-fuchsia-700 to-blue-700 text-transparent bg-clip-text">
              {{ fill_placeholders(selected_workflow.name2[language] || selected_workflow.name2.en, true) }}
            </span>:
          </div>

          <div class="text-xs font-normal text-gray-500 -mt-3 mb-2 flex flex-row items-center gap-1">
            <InformationCircleIcon class="h-4 w-4 inline"></InformationCircleIcon>
            {{ fill_placeholders(selected_workflow.help_text[language] || selected_workflow.help_text.en) }}
          </div>

          <div class="relative flex-none h-10 flex flex-row gap-3 items-center">
            <input type="search" name="search" @keyup.enter="create_collection" v-model="new_settings.user_input"
              autocomplete="off" v-if="selected_workflow?.supports_user_input"
              :placeholder="fill_placeholders(selected_workflow?.query_field_hint[language] || selected_workflow.query_field_hint.en)"
              class="w-full h-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
            <div class="" v-if="available_languages.length && !new_settings.auto_set_filters">
              <select v-model="new_settings.result_language" class="w-18 appearance-none ring-0 border-0 bg-transparent"
                v-tooltip.bottom="{ value: $t('CreateCollectionArea.language-of-the-query-and-search-results'), showDelay: 400 }">
                <option v-for="language in available_languages" :value="language.code">{{ language.flag }}</option>
              </select>
            </div>
            <button v-tooltip.bottom="{ value: $t('CreateCollectionArea.create-collection-using-this-workflow'), showDelay: 400 }"
              class="px-2 h-10 w-32 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
              @click="create_collection">
              {{ $t('CreateCollectionArea.go') }} <PaperAirplaneIcon class="inline h-5 w-5"></PaperAirplaneIcon>
            </button>
          </div>

          <div v-if="!new_settings.auto_set_filters && selected_workflow.supports_filters" class="flex flex-row gap-1 items-center">
            <div class="flex flex-row items-center gap-0 h-6">
              <button class="border border-gray-300 rounded-l-md px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
                @click="new_settings.retrieval_mode = 'keyword'"
                v-tooltip="{ value: $t('CreateCollectionArea.retrieval-mode-keyword'), showDelay: 400 }"
                :class="{ 'text-blue-500': new_settings.retrieval_mode === 'keyword', 'text-gray-400': new_settings.retrieval_mode != 'keyword' }">
                {{ $t('CreateCollectionArea.keyword-search') }}
              </button>
              <button
                class="border border-gray-300  rounded-none px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
                @click="new_settings.retrieval_mode = 'vector'"
                v-tooltip="{ value: $t('CreateCollectionArea.retrieval-mode-vector'), showDelay: 400 }"
                :class="{ 'text-blue-500': new_settings.retrieval_mode === 'vector', 'text-gray-400': new_settings.retrieval_mode != 'vector' }">
                {{ $t('CreateCollectionArea.meaning-search') }}
              </button>
              <button
                class="border border-gray-300 rounded-r-md  px-1 text-sm font-['Lexend'] font-normal hover:bg-gray-100"
                @click="new_settings.retrieval_mode = 'hybrid'"
                v-tooltip="{ value: $t('CreateCollectionArea.retrieval-mode-hybrid'), showDelay: 400 }"
                :class="{ 'text-blue-500': new_settings.retrieval_mode === 'hybrid', 'text-gray-400': new_settings.retrieval_mode != 'hybrid' }">
                {{ $t('CreateCollectionArea.hybrid-search') }}
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
                v-tooltip.bottom="{ value: $t('CreateCollectionArea.add-filters-and-change-search-options'), showDelay: 400 }"
                @click="(event) => { $refs.add_filter_menu.toggle(event) }">
                + {{ $t('CreateCollectionArea.filter') }}
              </button>
              <OverlayPanel ref="add_filter_menu">
                <AddFilterMenu @close="$refs.add_filter_menu.hide()" :filters="new_settings.filters">
                </AddFilterMenu>
              </OverlayPanel>
            </div>
          </div>

          <Message v-if="show_warning_about_missing_meaning_search" class="" :closable="false">
            {{ $t('CreateCollectionArea.vector-search-not-available-for-this-dataset') }}
          </Message>

          <!-- <Message v-if="!new_settings.auto_set_filters && using_meaning_for_non_english_search" class="" :closable="false">
            Meaning / hybrid search only works for English queries.
          </Message> -->

          <div v-if="!new_settings.auto_set_filters && query_uses_operators_and_meaning" class="text-xs text-gray-400 whitespace-pre-wrap">
            {{ $t('CreateCollectionArea.query-operators-not-supported-for-vector-search') }}
          </div>

          <div v-if="!new_settings.auto_set_filters && query_includes_other_quotes" class="text-xs text-gray-400">
            {{ $t('CreateCollectionArea.use-double-quotes-instead-of-single-quotes-to-search-for-phrases') }}
          </div>

          <SearchFilterList v-if="!new_settings.auto_set_filters"
            :removable="true"
            :filters="new_settings.filters"></SearchFilterList>

          <div v-if="selected_workflow?.supports_filters"
            class="ml-1 flex flex-row items-center"
            v-tooltip.top="{ value: ai_is_available ? '' : 'No more AI credits available' }">
            <InputSwitch v-model="new_settings.auto_set_filters" :binary="true" :disabled="!ai_is_available" class="scale-75" />
            <button class="ml-2 text-xs text-gray-500" :disabled="!ai_is_available"
              @click="new_settings.auto_set_filters = !new_settings.auto_set_filters">
              {{ $t('CreateCollectionArea.auto-set-filters') }}
            </button>
          </div>

          <Message v-if="selected_workflow.availability === 'preview'" class="" :closable="false">
            {{ $t('CreateCollectionArea.preview-feature') }}
          </Message>

        </div>

      </div>
    </div>

    <!-- example query box -->
    <div class="relative">
      <div v-if="example_queries.length" class="absolute top-4 text-sm text-gray-400">
        Try: <button class="underline hover:text-blue-500"
          @click="run_example_query(example_queries[example_query_index % example_queries.length])">
          "{{ example_queries[example_query_index % example_queries.length].query }}"
        </button>
      </div>
    </div>

    <!-- tool intro box -->
    <ToolIntroBox v-if="appState.organization?.tool_intro_text"></ToolIntroBox>

  </div>

</template>

<style >
#datasetdropdown > span {
  color: gray;
}
#datasetdropdown > div > svg {
  color: lightgray;
}
</style>
