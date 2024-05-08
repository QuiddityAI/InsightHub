<script setup>
import { useToast } from 'primevue/usetoast';
import {
  ArrowDownOnSquareIcon,
} from "@heroicons/vue/24/outline"
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
  props: ["collection_id", "class_name"],
  emits: [],
  data() {
    return {
      selected_converter: null,
      selected_format: null,
      available_formats: [
        { identifier: "xlsx", display_name: "Microsoft Excel (.xlsx)" },
        { identifier: "csv", display_name: "CSV" },
        { identifier: "json", display_name: "JSON (array of objects)" },
      ],
      is_loading: false,
      exported_data: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_converters() {
      const converters = {}
      for (const dataset of Object.values(this.appStateStore.datasets)) {
        for (const converter of dataset.applicable_export_converters) {
          converters[converter.identifier] = converter
        }
      }
      return Object.values(converters)
    }
  },
  mounted() {
    this.selected_converter = null
  },
  watch: {
  },
  methods: {
    get_exported_data() {
      const that = this
      this.is_loading = true
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        converter_identifier: this.selected_converter.identifier,
        format_identifier: this.selected_format.identifier,
      }
      httpClient
        .post(`/data_backend/collection/table/export`, body)
        .then(function (response) {
          that.exported_data = response.data
          that.is_loading = false
        })
    },
    download_file(filename, content) {
      const element = document.createElement('a')
      element.setAttribute('href', 'data:text/plain;charset=utf-8,' + encodeURIComponent(content))
      element.setAttribute('download', filename)
      element.style.display = 'none'
      document.body.appendChild(element)
      element.click()
      document.body.removeChild(element)
    },
  },
}
</script>

<template>
  <div class="mb-2 flex flex-col gap-2">
    <div class="flex flex-row items-center gap-2">
      <span class="flex-1 text-sm text-gray-500">Export item column as:</span>
      <div class="w-48">
        <select v-model="selected_converter"
          class="w-full h-full text-sm text-gray-500 rounded border-1 border-gray-300 focus:border-blue-500 focus:ring-blue-500">
          <option :value="null">
            Select Type
          </option>
          <option v-for="converter in available_converters" :value="converter">
            {{ converter.display_name }}
          </option>
        </select>
      </div>
    </div>
    <div class="flex flex-row items-center gap-2">
      <span class="flex-1 text-sm text-gray-500">Table Export Format:</span>
      <div class="w-48">
        <select v-model="selected_format"
          class="w-full h-full text-sm text-gray-500 rounded border-1 border-gray-300 focus:border-blue-500 focus:ring-blue-500">
          <option :value="null">
            Select Format
          </option>
          <option v-for="format in available_formats" :value="format">
            {{ format.display_name }}
          </option>
        </select>
      </div>
    </div>

    <button v-if="selected_converter && selected_format"
        class="px-3 py-1 rounded bg-blue-500 text-white hover:bg-blue-600"
        @click="get_exported_data()">
        Export
      </button>

    <p v-if="is_loading" class="text-sm text-gray-500">Loading...</p>

    <div v-if="exported_data?.value" class="mt-2">
      <button v-if="exported_data"
        class="px-2 py-2 flex flex-row items-center rounded bg-green-300 text-sm font-semibold hover:bg-blue-100/50"
        @click="download_file(exported_data.filename, exported_data.value)">
        Download {{ exported_data.filename }}
        <ArrowDownOnSquareIcon class="ml-2 h-5 w-5 inline"></ArrowDownOnSquareIcon>
      </button>
    </div>

  </div>
</template>

<style scoped>
</style>
