<script setup>

import { PaperAirplaneIcon } from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import Message from 'primevue/message';
import Checkbox from 'primevue/checkbox';
import OverlayPanel from 'primevue/overlaypanel';

import SearchFilterList from "../search/SearchFilterList.vue"
import AddFilterMenu from "../search/AddFilterMenu.vue"
import LanguageSelect from "../widgets/LanguageSelect.vue"
import BorderButton from "../widgets/BorderButton.vue"

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
      show_advanced_settings: false,
      settings_template: {
        dataset_id: null,
        auto_set_filters: true,
        user_input: '',
        result_language: null,
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
        auto_relax_query: true,
      },
      new_settings: {
        dataset_id: null,
        auto_set_filters: true,
        user_input: '',
        result_language: null,
        retrieval_mode: 'hybrid',
        ranking_settings: null,
        related_organization_id: null,
        auto_relax_query: true,
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
      const dataset_languages = this.appStateStore.available_language_filters.map(item => languages.find(lang => lang.code == item[1]))
      const any_language = [{ name: 'any', code: null, flag: '🌍' }]
      return any_language.concat(dataset_languages)
    },
    query_uses_operators_and_meaning() {
      const uses_meaning = ["vector", "hybrid"].includes(this.new_settings.retrieval_mode)
      const operators = [" AND ", " OR ", " NOT "]
      const uses_operators = operators.some((op) => this.new_settings.user_input?.includes(op))
      return uses_operators && uses_meaning
    },
    query_includes_other_quotes() {
      const other_quotes = ["'", "`", "´", "‘", "’", "“", "”", "„", "‟", "❛", "❜", "❝", "❞", "＇", "＂"]
      const query = this.new_settings.user_input || ""
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
    if (this.collectionStore.collection.most_recent_search_task?.settings
      && Object.keys(this.collectionStore.collection.most_recent_search_task?.settings).length > 0
      && this.collectionStore.collection.most_recent_search_task?.settings.search_type == 'external_input') {
      this.new_settings = JSON.parse(JSON.stringify(this.collectionStore.collection.most_recent_search_task?.settings))
      this.new_settings.auto_approve = false
      this.new_settings.exit_search_mode = false
      this.new_settings.keyword_query = undefined  // this comes from last search, but should be empty
    } else {
      this.new_settings = JSON.parse(JSON.stringify(this.settings_template))
    }

    if (this.new_settings.dataset_id === null) {
      this.new_settings.dataset_id = this.appStateStore.settings.search.dataset_ids.length ? this.appStateStore.settings.search.dataset_ids[0] : null
    }
    this.eventBus.on("datasets_are_loaded", this.on_dataset_loaded)
  },
  unmounted() {
    this.eventBus.off("datasets_are_loaded", this.on_dataset_loaded)
  },
  watch: {
    'new_settings.dataset_id'(new_val, old_val) {
      // TODO: the logic to change dataset dependend options should be moved somewhere else, this is just retrofitting
      if (new_val === null && new_val === undefined) return
      this.appStateStore.settings.search.dataset_ids = [new_val]
      this.appStateStore.on_selected_datasets_changed()
    },
  },
  methods: {
    on_dataset_loaded() {
      if (this.new_settings.dataset_id === null) {
        this.new_settings.dataset_id = this.appStateStore.settings.search.dataset_ids.length ? this.appStateStore.settings.search.dataset_ids[0] : null
      }
    },
    run_search_task() {
      const that = this
      if (!this.new_settings.dataset_id) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please select a source dataset', life: 2000 })
        return
      }
      if (!this.new_settings.user_input && !this.new_settings.filters?.length) {
        this.$toast.add({ severity: 'error', summary: 'Error', detail: 'Please enter a query', life: 2000 })
        return
      }
      this.new_settings.related_organization_id = this.appStateStore.organization_id
      const body = {
        search_task: this.new_settings,
        collection_id: this.collectionStore.collection_id,
        class_name: this.collectionStore.class_name,
        wait_for_ms: 200,  // wait in case search task is quick and in that case reduce flickering
      }
      httpClient
        .post("/api/v1/search/run_search_task", body)
        .then(function (response) {
          that.collectionStore.update_collection({update_items: true}, () => {
            that.$emit("close")
          })
        })
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-3 mb-1">

    <!-- <Message severity="info">
      To search for something new / unrelated to this collection, please create a new collection instead.
    </Message> -->

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
        <input type="search" name="search" @keyup.enter="run_search_task" v-model="new_settings.user_input"
          autocomplete="off"
          :placeholder="`Search...`"
          class="w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
        <LanguageSelect v-if="available_languages.length && !new_settings.auto_set_filters"
          :available_language_codes="appState.available_language_filters.map(item => item[1])"
          v-model="new_settings.result_language"
          :offer_wildcard="true"
          tooltip="Language of the query and search results">
        </LanguageSelect>
        <button v-tooltip.bottom="{ value: 'Submit', showDelay: 400 }"
          class="px-2 h-9 w-60 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
          @click="run_search_task">
          Go <PaperAirplaneIcon class="inline h-5 w-5"></PaperAirplaneIcon>
        </button>
      </div>

      <div
        class="ml-1 flex flex-row items-center"
        v-tooltip.top="{ value: ai_is_available ? '' : 'No more AI credits available' }">
        <Checkbox v-model="new_settings.auto_set_filters" class="" :binary="true" :disabled="!ai_is_available" />
        <button class="ml-2 text-xs text-gray-500" :disabled="!ai_is_available"
          @click="new_settings.auto_set_filters = !new_settings.auto_set_filters">
          Auto-detect best search strategy and required filters from query
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
          <option :value="new_settings.ranking_settings">
            {{ new_settings.ranking_settings.title }}
          </option>
          <option v-for="ranking_settings in appState.available_ranking_options" :value="ranking_settings">
            {{ ranking_settings.title }}
          </option>
        </select>
        <div class="flex-1"></div>
        <div class="flex flex-row items-center gap-2 h-6">
          <BorderButton
            v-tooltip.bottom="{ value: 'Add filters and change search options', showDelay: 400 }"
            @click="(event) => { $refs.add_filter_menu.toggle(event) }">
            + Filter
          </BorderButton>
          <OverlayPanel ref="add_filter_menu">
            <AddFilterMenu @close="$refs.add_filter_menu.hide()" :filters="new_settings.filters">
            </AddFilterMenu>
          </OverlayPanel>
          <BorderButton :highlighted="show_advanced_settings"
            v-tooltip.bottom="{ value: 'Show advanced settings', showDelay: 400 }"
            @click="show_advanced_settings = !show_advanced_settings">
            {{ $t('SearchTaskDialog.advanced-settings') }}
          </BorderButton>
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

      <div class="flex flex-col gap-2" v-if="show_advanced_settings">
        <div class="flex flex-row gap-2 items-center">

          <div class="flex flex-row items-center gap-1" v-if="appState.user.is_staff">
            <Checkbox v-model="new_settings.auto_relax_query"
              inputId="search_task_auto_relax_query" size="small" :binary="true" class="scale-75" />
            <label for="search_task_auto_relax_query" class="text-sm text-gray-500"
              v-tooltip.bottom="{ value: $t('SearchTaskDialog.query-relaxation-tooltip'), showDelay: 400 }">
              {{ $t('SearchTaskDialog.auto-relax-query') }}
            </label>
          </div>

        </div>
      </div>

    </div>

  </div>

</template>

<style scoped>
</style>
