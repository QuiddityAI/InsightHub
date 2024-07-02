<script setup>
import {
  PaperAirplaneIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import Listbox from 'primevue/listbox';
import ProgressSpinner from 'primevue/progressspinner';
import Message from 'primevue/message';

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
      question: "",
      is_processing: false,
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
    example_queries() {
      if (this.appStateStore.settings.search.dataset_ids.length === 0) {
        return []
      }
      return this.appStateStore.datasets[this.appStateStore.settings.search.dataset_ids[0]]?.advanced_options.example_questions || []
    },
  },
  mounted() {
    // increase example query index every few seconds
    setInterval(() => {
      this.example_query_index = this.example_query_index + 1
    }, 10000)
  },
  watch: {
  },
  methods: {
    create_chat() {
      if (this.is_processing) return
      if (!this.question) {
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Please enter a question', life: 5000})
        return
      }
      if (this.appStateStore.settings.search.dataset_ids.length === 0) {
        this.$toast.add({severity: 'error', summary: 'Error', detail: 'Please select at least one source', life: 5000})
        return
      }
      if (!this.appStateStore.check_if_search_is_allowed({use_credit: false})) return

      this.is_processing = true
      this.appStateStore.settings.search.all_field_query = this.question
      this.appStateStore.create_chat_from_search_settings(() => {
        this.is_processing = false
        // chat is opened by signal on event bus
      })
    },
    run_example_question(example) {
      this.question = example.question
      this.create_chat()
    },
  },
}
</script>

<template>
  <div class="flex flex-col justify-center">

    <div class="ml-1 mt-3 flex flex-row gap-3">
      <h2 class="font-bold text-gray-600">New Chat</h2>
    </div>

    <div class="flex-1"></div>

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
              @keyup.enter="run_smart_search()"
              v-model="question"
              autocomplete="off"
              :disabled="is_processing"
              :placeholder="`Ask a question`"
              class="h-full w-full rounded-md border-0 py-1.5 text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6" />
          </div>
          <button v-if="!is_processing"
            v-tooltip.bottom="{value: 'Submit', showDelay: 400}"
            class="ml-2 px-2 h-9 w-9 rounded-md shadow-sm border-gray-300 border bg-gray-100 hover:bg-blue-100/50 text-sm text-gray-500"
            @click="create_chat()">
            <PaperAirplaneIcon class="h-5 w-5"></PaperAirplaneIcon>
          </button>
          <div class="flex items-center justify-center">
            <ProgressSpinner v-if="is_processing" class="ml-1 w-5 h-5"></ProgressSpinner>
          </div>
        </div>

        <div class="relative">
          <div v-if="example_queries.length" class="absolute top-10 text-sm text-gray-400">
            Try: <button class="underline hover:text-blue-500"
              @click="run_example_question(example_queries[example_query_index % example_queries.length])">
              "{{ example_queries[example_query_index % example_queries.length].question }}"
            </button>
          </div>
        </div>

      </div>

    </div>

    <div class="mt-4 flex flex-row items-end">
      <img src="/assets/up_left_arrow.svg" class="ml-12 mr-4 pb-1 w-8" />
      <span class="text-gray-500 italic">Want to chat with your own files? Upload them at the top.</span>
    </div>
    <div class="flex-1"></div>
  </div>

</template>

<style scoped>
</style>
