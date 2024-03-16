<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import InputGroup from 'primevue/inputgroup';
import InputGroupAddon from 'primevue/inputgroupaddon';
import FileUpload from 'primevue/fileupload';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
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
  props: ["dataset"],
  emits: ["close"],
  data() {
    return {
      selected_import_type: null,
      import_types: [
        { name: "Scientific Article as PDF", value: "scientific_pdf" },
        { name: "Scientific Articles as CSV", value: "scientific_csv" },
        { name: "Scientific Articles as Excel", value: "scientific_xls" },
      ],
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
  },
  watch: {
  },
  methods: {
    delete_dataset() {
      alert("delete dataset")
    },
  },
}
</script>

<template>
  <div>
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ dataset.name }}</span>
      <div class="flex-1"></div>
      <button
        @click="delete_dataset"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <!-- FIXME: implement access control -->
    <div v-if="dataset.admins?.includes(appState.user.id) || true">
      <h3 class="text-md text-gray-600 font-semibold">
        Upload Files
      </h3>
      <div class="ml-2 mb-3 mt-2 flex flex-col gap-2">
        <label class="mr-2 text-sm text-gray-700" for="import_type">Import Type:</label>
        <Dropdown
          id="import_type"
          v-model="selected_import_type"
          :options="import_types"
          optionLabel="name"
          placeholder="Select an import type"/>
        <FileUpload name="demo[]" url="/api/upload" @upload="onAdvancedUpload($event)" :multiple="true" accept="image/*" :maxFileSize="1000000">
          <template #empty>
            <p>Drag and drop files to here to upload.<br>
              You can upload individual files or zip files with multiple files.
            </p>
          </template>
        </FileUpload>
      </div>
      <h3 class="text-md text-gray-600 font-semibold">
        Upload using API
      </h3>
      <div class="ml-2">
        <p class="mb-1 text-gray-700">
          You can use the following command to upload data to this dataset:
        </p>
        <code class="text-sm text-gray-500 font-mono">
          curl "/api/datasets/{{ dataset.id }}/insert_many/" -X POST -H "Authorization: Bearer &lt;your_token&gt;" -H "Content-Type: application/json" -d '{"data": [{"name": "John Doe", "age": 30}, {"name": "Jane Doe", "age": 25}]}'
        </code>
      </div>
    </div>

    <!-- FIXME: implement access control -->
    <div v-if="!dataset.admins?.includes(appState.user.id) && false">
      <span class="text-sm text-gray-500">
        You can only upload to your own datasets.
      </span>
    </div>
  </div>
</template>

<style scoped>
</style>
