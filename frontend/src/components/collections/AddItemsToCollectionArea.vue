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
  props: ["collection"],
  emits: [],
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
    <div class="flex flex-row items-center">
      <Dropdown id="schema_dropdown"
        v-model="selected_schema"
        :options="available_schemas" optionLabel="name"
        placeholder="Select a Schema"
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
        :dataset_id="selected_dataset_id"
        ></AddItemsToDatasetArea>
    </div>
  </div>

</template>

<style scoped>
</style>
