<script setup>
import { useToast } from 'primevue/usetoast';
import Button from 'primevue/button';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import DatasetDetails from "./DatasetDetails.vue"
import CreateDatasetDialog from './CreateDatasetDialog.vue';
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
      selected_dataset: null,
      create_dataset_dialog_visible: false,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    your_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => dataset.admins.includes(this.appStateStore.user.id))
    },
    organization_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => !dataset.admins.includes(this.appStateStore.user.id) && dataset.is_public === false)
    },
    public_datasets() {
      return Object.values(this.appStateStore.datasets).filter(dataset => !dataset.admins.includes(this.appStateStore.user.id) && dataset.is_public === true)
    },
  },
  mounted() {
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="mt-2 mb-2 flex flex-col gap-2">
    <div
      v-if="!selected_dataset"
      v-for="category in [{items: your_datasets, name: 'Your Datasets'}, {items: organization_datasets, name: 'Organization'}, {items: public_datasets, name: 'Public'}]"
      class="rounded-md bg-gray-100 pb-1 pl-3 pr-2 pt-2">
      <div class="flex flex-row gap-3">
        <span class="font-bold text-gray-600">{{ category.name }}</span>
      </div>
      <ul class="mt-3">
        <li v-for="dataset in category.items"
          class="mb-2 flex flex-row rounded-md bg-white py-[3px] pr-2 hover:bg-blue-500/10">
          <button class="flex flex-1 flex-row" @click="selected_dataset = dataset">
            <span class="pl-2 text-sm text-gray-500">
              {{ dataset.name }}
            </span>
            <div class="flex-1"></div>

          </button>
        </li>
      </ul>
      <div v-if="category.items.length === 0" class="mb-2 text-sm text-gray-500">
        No datasets yet
      </div>
      <Button v-if="category.items === your_datasets" class="h-6 mb-2 mt-1"
        @click="create_dataset_dialog_visible = true"
        label="Create new dataset">
      </Button>
      <CreateDatasetDialog v-if="category.items === your_datasets && create_dataset_dialog_visible" v-model:visible="create_dataset_dialog_visible" />
    </div>

    <DatasetDetails
      v-if="selected_dataset"
      :dataset="selected_dataset"
      @close="selected_dataset = null"
      />

  </div>

</template>

<style scoped>
</style>
