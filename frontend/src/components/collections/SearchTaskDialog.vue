<script setup>
import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';
import { PaperAirplaneIcon } from "@heroicons/vue/24/outline"

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { languages } from "../../utils/utils"

const appState = useAppStateStore()
const mapState = useMapStateStore()
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
        dataset_ids: [],
      },
      new_settings: {
        dataset_ids: [],
      },
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_languages() {
      return this.appStateStore.available_language_filters.map(item => languages.find(lang => lang.code == item[1]))
    },
  },
  mounted() {
    this.new_settings = JSON.parse(JSON.stringify(this.collection.research_task || this.settings_template))
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <div
      class="flex flex-row items-center justify-center gap-6 text-gray-500 font-semibold">
      Search in:
      <button v-for="dataset in Object.values(appState.datasets).slice(0, 2)" @click="new_settings.dataset_ids = [dataset.id]"
        class="text-md px-3 py-1 hover:text-blue-500"
        :class="{
          'underline': new_settings.dataset_ids.includes(dataset.id) }"
        v-tooltip.bottom="{ value: dataset.short_description, showDelay: 0 }">
        {{ dataset.name }}
      </button>
      <button @click="appState.selected_app_tab = 'datasets'"
        class="text-md font-normal px-3 py-1 hover:text-blue-500">
        Upload your own files
      </button>
    </div>

    <div class="relative flex-1 h-9 flex flex-row items-center">
      <input
        type="search"
        name="search"
        @keyup.enter="use_smart_search ? run_smart_search() : appState.request_search_results()"
        v-model="appState.settings.search.all_field_query"
        autocomplete="off"
        :disabled="processing_smart_search"
        :placeholder="`Describe what ${appState.settings.search.dataset_ids.length ? appState.datasets[appState.settings.search.dataset_ids[0]]?.schema.entity_name || '' : ''} you want to find`"
        class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
      <div class="absolute right-5" v-if="available_languages.length && !use_smart_search">
        <select v-model="appState.settings.search.result_language" class="w-18 appearance-none ring-0 border-0 bg-transparent"
          v-tooltip.bottom="{ value: 'Language of the query and search results', showDelay: 400 }">
          <option v-for="language in available_languages" :value="language.code">{{ language.flag }}</option>
        </select>
      </div>
    </div>
    <button v-if="!processing_smart_search"
      v-tooltip.bottom="{value: 'Submit', showDelay: 400}"
      class="px-2 h-9 w-60 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
      @click="$emit('close')">
      Save / Do Research Now <PaperAirplaneIcon class="inline h-5 w-5"></PaperAirplaneIcon>
    </button>

    Presets:
    - Quick search
    - Short Answer
    - Evalute Items
    - Long Report
    - Custom Settings

    <br>
    <hr>
    [ ] eval candidates<br>
    [ ] auto-add<br>
    [ ] auto add columns<br>
    <hr>
    [ ] create subqueries<br>

  </div>

</template>

<style scoped>
</style>
