<script setup>
import { useToast } from 'primevue/usetoast';
import Dropdown from 'primevue/dropdown';

import AddItemsToDatasetArea from '../datasets/AddItemsToDatasetArea.vue';

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
  props: ["collection", "collection_class"],
  emits: ["items_added"],
  data() {
    return {
      available_schemas: [],
      selected_schema: null,
      selected_dataset_id: -1,
      selected_import_converter: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    available_datasets() {
      const datasets = [
        { id: -1, name: "Default Dataset" },
      ]
      if (this.selected_schema) {
        for (const dataset of Object.values(this.appStateStore.datasets)) {
          if (dataset.schema.identifier === this.selected_schema.identifier) {
            datasets.push({ id: dataset.id, name: dataset.name })
          }
        }
      }
      return datasets
    },
  },
  mounted() {
    this.get_schemas()
  },
  watch: {
    selected_schema() {
      this.selected_dataset_id = -1
    },
  },
  methods: {
    get_schemas() {
      const that = this
      const body = {
        organization_id: that.appStateStore.organization.id,
      }
      httpClient.post(`/org/data_map/get_dataset_schemas`, body)
      .then(function (response) {
        that.available_schemas = response.data
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <div class="flex flex-col gap-3">
    <span class="text-gray-500">
      You can add items either by searching for them in the 'Explore' tab and adding them there to this collection, or by uploading external items here.
    </span>
    <div class="flex flex-row items-center">
      <Dropdown id="schema_dropdown"
        v-model="selected_schema"
        :options="available_schemas" optionLabel="name"
        placeholder="Select Data Type"
        class="" />
    </div>
    <div class="flex flex-row items-center">
      <Dropdown id="dataset_dropdown"
        v-if="selected_schema"
        v-model="selected_dataset_id"
        :options="available_datasets" optionLabel="name" optionValue="id"
        placeholder="Select a Dataset"
        class="" />
    </div>
    <div class="flex flex-row gap-2 items-center">
      <AddItemsToDatasetArea
        v-if="selected_schema"
        :schema="selected_schema"
        :preselected_import_converter="null"
        :target_collection="collection"
        :target_collection_class="collection_class"
        :dataset_id="selected_dataset_id"
        @items_added="$emit('items_added')"
        ></AddItemsToDatasetArea>
    </div>
  </div>

</template>

<style scoped>
</style>
