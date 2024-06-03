<script setup>
import { useToast } from 'primevue/usetoast';
import Dialog from 'primevue/dialog';
import InputText from 'primevue/inputtext';
import Dropdown from 'primevue/dropdown';
import Button from 'primevue/button';
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
  emits: ["update:visible"],
  data() {
    return {
      name: "",
      available_schemas: [],
      selected_schema: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.get_templates()
  },
  watch: {
  },
  methods: {
    get_templates() {
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
    create_dataset() {
      if (!this.name || this.selected_schema === null) {
        return
      }
      const that = this
      const body = {
        name: that.name,
        organization_id: that.appStateStore.organization.id,
        schema_identifier: that.selected_schema.identifier,
        from_ui: true,
      }
      httpClient.post(`/org/data_map/create_dataset_from_schema`, body)
      .then(function (response) {
        const dataset = response.data
        that.appStateStore.prepare_dataset_object(dataset)
        that.appStateStore.datasets[response.data.id] = dataset
        that.$emit("update:visible", false)
      })
      .catch(function (error) {
        console.error(error)
      })
    },
  },
}
</script>

<template>
  <Dialog modal header="Create Dataset">
    <div class="flex flex-col gap-2">
      <label for="new_dataset_name">Dataset Name</label>
      <InputText id="new_dataset_name" v-model="name" />
    </div>
    <div class="mt-2 flex flex-col gap-2">
      <label for="schema_dropdown">Schema</label>
      <Dropdown id="schema_dropdown"
        v-model="selected_schema"
        :options="available_schemas" optionLabel="name"
        placeholder="Select a Schema"
        class="" />
      <small id="schema_dropdown-help">The schema determines the fields of the dataset, how they are rendered and what import types are available.</small>
    </div>
    <Button label="Create" class="mt-3" @click="create_dataset()" :disabled="!name || selected_schema === null"></Button>
  </Dialog>
</template>

<style scoped>
</style>
