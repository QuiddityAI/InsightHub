<script setup>
import {
  QuestionMarkCircleIcon,
} from "@heroicons/vue/24/outline"
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
      dialog_is_visible: true,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.get_schemas()
  },
  watch: {
    dialog_is_visible() {
      this.$emit("update:visible", false)
    },
    selected_schema() {
      this.name = this.selected_schema ? `My ${this.selected_schema.name}` : ""
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
  <Dialog modal header="Create Dataset" v-model:visible="dialog_is_visible">
    <div class="flex flex-col gap-2">
      <label for="schema_dropdown"
        v-tooltip.top="{ value: 'The data type (\'schema\') determines the fields of the dataset, how they are rendered and what import types are available.', showDelay: 400 }">
        Data Type <QuestionMarkCircleIcon class="inline h-5 w-5 text-gray-400"></QuestionMarkCircleIcon>
    </label>
      <Dropdown id="schema_dropdown"
        v-model="selected_schema"
        :options="available_schemas" optionLabel="name"
        placeholder="Select a Schema"
        class="" />

    </div>
    <div v-if="selected_schema" class="mt-5 flex flex-col gap-2">
      <label for="new_dataset_name">Dataset Name</label>
      <InputText id="new_dataset_name" v-model="name" />
      <small id="new_dataset_name-help">We recommend to create just one dataset per data type and use collections to further structure the items, as searching across multiple datasets can result in imprecise rankings.</small>
    </div>
    <Button label="Create" class="mt-5" @click="create_dataset()" :disabled="!name || selected_schema === null"></Button>
  </Dialog>
</template>

<style scoped>
</style>
