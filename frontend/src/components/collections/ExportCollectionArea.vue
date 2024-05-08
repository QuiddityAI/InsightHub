<script setup>
import { useToast } from 'primevue/usetoast';
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
    selected_converter() {
      if (!this.selected_converter) return
      this.get_exported_data()
    },
  },
  methods: {
    get_exported_data() {
      const that = this
      this.is_loading = true
      const body = {
        collection_id: this.collection_id,
        class_name: this.class_name,
        converter_identifier: this.selected_converter.identifier,
      }
      httpClient
        .post(`/data_backend/collection/export`, body)
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
    <div class="w-40">
      <select v-model="selected_converter"
        class="w-full h-full mr-4 text-sm text-gray-500 border-1 border-gray-300 focus:border-blue-500 focus:ring-blue-500">
        <option :value="null">
          Select Export Type
        </option>
        <option v-for="converter in available_converters" :value="converter">
          {{ converter.display_name }}
        </option>
      </select>
    </div>

    <p v-if="is_loading" class="text-sm text-gray-500">Loading...</p>

    <div v-if="exported_data?.value" class="">
      <button v-if="exported_data"
        class="px-2 py-1 rounded bg-gray-100 hover:bg-blue-100/50"
        @click="download_file(exported_data.filename, exported_data.value)">
        Download {{ exported_data.filename }}
      </button>
    </div>

  </div>
</template>

<style scoped>
</style>
