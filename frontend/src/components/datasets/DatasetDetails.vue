<script setup>
import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import {
  ChevronLeftIcon,
  TrashIcon,
} from "@heroicons/vue/24/outline"
import FileUpload from 'primevue/fileupload';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
import Badge from 'primevue/badge';
import Message from 'primevue/message';
import ProgressBar from 'primevue/progressbar';
import Checkbox from 'primevue/checkbox';

import CollectionItem from "../collections/CollectionItem.vue";
import SelectCollection from '../collections/SelectCollection.vue';
import AddItemsToDatasetArea from './AddItemsToDatasetArea.vue';

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
      preselected_import_converter: null,
      visible_area: "upload_files",
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.preselected_import_converter = this.dataset.schema.applicable_import_converters.length ? this.dataset.schema.applicable_import_converters[0] : null
    this.get_dataset_additional_info()
  },
  watch: {
    'dataset.is_public'() {
      this.update_dataset()
    },
    'dataset.is_organization_wide'() {
      this.update_dataset()
    },
  },
  methods: {
    get_dataset_additional_info() {
      const that = this
      httpClient
        .post("/org/data_map/dataset", { dataset_id: this.dataset.id, additional_fields: ["item_count"]})
        .then(function (response) {
          // don't overwrite the whole dataset object as other fields need special handling
          that.dataset.item_count = response.data.item_count
        })
        .catch(function (error) {
          console.error(error)
        })
    },
    update_dataset() {
      const that = this
      const body = {
        dataset_id: that.dataset.id,
        updates: {
          is_public: that.dataset.is_public,
          is_organization_wide: that.dataset.is_organization_wide,
        },
      }
      httpClient.post(`/org/data_map/change_dataset`, body)
      .then(function (response) {
        that.$toast.add({severity:'success', summary: 'Success', detail: 'Dataset updated successfully.', life: 3000})
      })
      .catch(function (error) {
        console.error(error)
      })
    },
    delete_dataset() {
      if (!this.dataset.created_in_ui) {
        this.$toast.add({severity:'info', summary: 'Info', detail: 'You cannot delete this dataset because it was not created from the UI. Use the backend to delete it.'})
        return
      }
      if (!confirm("Are you sure you want to delete this dataset, all of its data, and related collection items? This action cannot be undone.")) {
        return
      }
      const that = this
      const body = {
        dataset_id: that.dataset.id,
      }
      httpClient.post(`/org/data_map/delete_dataset`, body)
      .then(function (response) {
        delete that.appStateStore.datasets[that.dataset.id]
        that.$emit("close")
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div class="h-full">
    <div class="mb-3 ml-1 mt-3 flex flex-row gap-3">
      <button
        @click="$emit('close')"
        class="h-6 w-6 rounded text-gray-400 hover:bg-gray-100">
        <ChevronLeftIcon></ChevronLeftIcon>
      </button>
      <span class="font-bold text-gray-600">{{ dataset.name }}</span>
      <span class="font-normal text-gray-400" v-if="dataset.schema.name">({{ dataset.schema.name }})</span>
      <div class="flex-1"></div>
      <button
          @click="appState.show_global_map([dataset.id])"
          title="Show all items (or a representative subset if there are too many)"
          class="ml-1 rounded-md px-2 h-7 text-sm text-gray-500 bg-gray-100 hover:bg-blue-100/50">
          {{ dataset.item_count < 2000 ? 'Show all items' : 'Show representative overview' }}
        </button>
      <button
        v-if="dataset.admins?.includes(appState.user.id)"
        @click="delete_dataset"
        class="flex h-6 w-6 items-center justify-center rounded text-gray-400 hover:bg-gray-100 hover:text-red-500">
        <TrashIcon class="h-4 w-4"></TrashIcon>
      </button>
    </div>

    <div class="flex flex-col ml-2 mb-4 mt-2 gap-1">
      <p class="text-gray-600 text-sm">
        Items in this dataset: <b>{{ dataset.item_count !== undefined ? dataset.item_count.toLocaleString() : 'unknown' }}</b>
      </p>
      <div>

      </div>
      <div class="flex flex-col gap-2">
        <label class="flex items-center" v-if="appState.user.is_staff || dataset.is_public">
          <input type="checkbox" v-model="dataset.is_public" :disabled="!dataset.admins?.includes(appState.user.id) || !appState.user.is_staff">
          <span class="ml-2 text-sm text-gray-600">Public for everyone on the internet {{ !appState.user.is_staff ? '(can only be changed by staff)': '' }}</span>
        </label>
        <label class="flex items-center">
          <input type="checkbox" v-model="dataset.is_organization_wide" :disabled="!dataset.admins?.includes(appState.user.id)">
          <span class="ml-2 text-sm text-gray-600">Available to other organization members</span>
        </label>
      </div>
    </div>

    <div v-if="dataset.admins?.includes(appState.user.id)">
      <button class="w-full hover:bg-gray-100" @click="visible_area = 'upload_files'">
        <h3 class="text-left text-md text-gray-600 font-semibold">
          Upload Files
        </h3>
      </button>
      <AddItemsToDatasetArea v-if="visible_area == 'upload_files'"
        class="ml-2"
        :schema="dataset.schema"
        :preselected_import_converter="preselected_import_converter"
        :target_collection="null"
        :dataset_id="dataset.id"
        @items_added="get_dataset_additional_info"
        />
      <button v-if="appState.dev_mode" class="mt-2 w-full hover:bg-gray-100" @click="visible_area = 'upload_using_api'">
        <h3 class="text-left text-md text-gray-600 font-semibold">
          Upload using API
        </h3>
      </button>
      <div v-if="visible_area == 'upload_using_api'" class="ml-2">
        <p class="mt-2 mb-1 text-gray-700">
          You can use the following command to upload data to this dataset:
        </p>
        <code class="text-sm text-gray-500 font-mono">
          curl "/api/datasets/{{ dataset.id }}/insert_many/" -X POST -H "Authorization: Bearer &lt;your_token&gt;" -H "Content-Type: application/json" -d '{"data": [{"name": "John Doe", "age": 30}, {"name": "Jane Doe", "age": 25}]}'
        </code>
      </div>
    </div>

    <div v-if="!dataset.admins?.includes(appState.user.id)">
      <span class="text-sm text-gray-500">
        You can't upload files to this dataset because you are not an admin.
      </span>
    </div>
  </div>
</template>

<style scoped>
</style>
