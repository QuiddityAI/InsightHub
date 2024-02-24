<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()
</script>

<script>
export default {
  props: ['modelValue'],  // needed to make this component v-model-able
  emits: ['update:modelValue'],
  data() {
    return {
      selected_collection_id: null,
      selected_collection_class: "_default",
      target_ds_and_vector_field: [null, null],
    }
  },
  watch: {
    selected_collection_id() {
      this.update_modelValue()
      if (this.selected_collection_id === null) {
        this.selected_collection_class = "_default"
        return
      }
      this.selected_collection_class =
      this.appStateStore.collections[
          this.appStateStore.collections.findIndex((e) => e.id == this.selected_collection_id)
        ].actual_classes[0].name
    },
    selected_collection_class() {
      this.update_modelValue()
    },
    target_ds_and_vector_field() {
      this.update_modelValue()
    },
  },
  methods: {
    update_modelValue() {
      this.$emit('update:modelValue', {
        collection_id: this.selected_collection_id,
        class_name: this.selected_collection_class,
        target_dataset_id: this.target_ds_and_vector_field[0],
        target_vector_field: this.target_ds_and_vector_field[1],
      })
    }
  },
  mounted() {
    if (this.appStateStore.last_used_collection_id === null) {
      this.selected_collection_id = this.appStateStore.collections.length ? this.appStateStore.collections[0].id : null
    } else {
      this.selected_collection_id = this.appStateStore.last_used_collection_id
    }
    this.target_ds_and_vector_field = this.appStateStore.available_vector_fields.find((ds_and_field) => ds_and_field[1] === this.appStateStore.settings.vectorize.map_vector_field)
    if (!this.target_ds_and_vector_field) {
      this.target_ds_and_vector_field = this.appStateStore.available_vector_fields[0]
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
  }
}
</script>

<template>
  <div class="flex flex-row">
    <div class="w-32 h-6">
      <select
        v-model="selected_collection_id"
        class="w-full rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option v-for="collection in appState.collections" :value="collection.id">
          {{ collection.name }}
        </option>
      </select>
    </div>
    <div class="w-24 h-6">
      <select
        v-if="selected_collection_id !== null"
        v-model="selected_collection_class"
        class="w-full rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option
          v-for="class_details in appState.collections[
            appState.collections.findIndex((e) => e.id == selected_collection_id)
          ].actual_classes"
          :value="class_details.name">
          {{ class_details.name == "_default" ? "Items" : class_details.name }}
        </option>
      </select>
    </div>
    <div class="flex-1 h-6">
      <select
        v-model="target_ds_and_vector_field"
        class="w-full py-0 rounded border-transparent text-sm text-gray-500 focus:border-blue-500 focus:ring-blue-500">
        <option v-for="item in appState.available_vector_fields" :value="item" selected>
          {{ appState.datasets[item[0]]?.name }}: {{ item[1] }}
        </option>
      </select>
    </div>
  </div>
</template>
