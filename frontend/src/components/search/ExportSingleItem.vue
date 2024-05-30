<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
const appState = useAppStateStore()
const mapState = useMapStateStore()
const toast = useToast()

const _navigator = navigator
const _window = window

</script>

<script>

export default {
  inject: ["eventBus"],
  props: ["dataset", "item"],
  emits: [],
  data() {
    return {
      selected_converter: null,
      exported_data: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.selected_converter = this.dataset.schema.applicable_export_converters[0]
  },
  watch: {
    selected_converter() {
      this.get_exported_data()
    },
  },
  methods: {
    get_exported_data() {
      const that = this
      const body = {
        dataset_id: this.dataset.id,
        item_id: this.item._id,
        converter_identifier: this.selected_converter.identifier,
      }
      httpClient
        .post(`/data_backend/document/export`, body)
        .then(function (response) {
          that.exported_data = response.data
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
    <div class="mb-2 flex flex-row gap-2">
      <button v-for="export_converter in dataset.schema.applicable_export_converters"
        @click="selected_converter = export_converter; exported_data = null"
        class="px-2 rounded bg-gray-100 hover:bg-blue-100/50"
        :class="{'text-blue-600': selected_converter?.id == export_converter.id}">
        {{ export_converter.display_name }}
      </button>
    </div>

    <div v-if="selected_converter?.preview_as_text && exported_data" class="flex-none h-48 flex flex-col gap-2">
      <textarea
        v-model="exported_data.value" class="w-full h-full" readonly></textarea>
    </div>

    <div v-if="exported_data?.value" class="flex flex-row gap-2">
      <button v-if="selected_converter?.preview_as_text"
        @click="_window.isSecureContext ? _navigator.clipboard.writeText(exported_data.value) : _window.prompt('Copy to clipboard: Ctrl+C, Enter', exported_data.value)"
        class="px-2 py-1 w-40 rounded bg-gray-100 hover:bg-blue-100/50">
        Copy to Clipboard
      </button>
      <button v-if="exported_data"
        class="px-2 py-1 w-40 rounded bg-gray-100 hover:bg-blue-100/50"
        @click="download_file(exported_data.filename, exported_data.value)">
        Download {{ exported_data.filename }}
      </button>
    </div>

  </div>
</template>

<style scoped>
</style>
