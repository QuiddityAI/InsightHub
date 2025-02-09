<script setup>
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"

const appState = useAppStateStore()
</script>

<script>
export default {
  props: [],
  emits: [],
  data() {
    return {
      selected_collection_id: null,
      selected_collection_class: "_default",
    }
  },
  expose: ["selected_collection_id", "selected_collection_class"],
  watch: {
    selected_collection_id() {
      const collection = this.appStateStore.collections[
          this.appStateStore.collections.findIndex((e) => e.id == this.selected_collection_id)
        ]
      this.selected_collection_class = collection?.actual_classes[0].name
    },
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {
    if (this.appStateStore.last_used_collection_id === null) {
      this.selected_collection_id = this.appStateStore.collections.length ? this.appStateStore.collections[0].id : null
    } else {
      this.selected_collection_id = this.appStateStore.last_used_collection_id
    }
  },
  methods: {},
}
</script>

<template>
  <div class="flex flex-row">
    <select
      v-model="selected_collection_id"
      class="mr-2 h-8 w-32 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
      <option v-for="collection in appState.collections" :value="collection.id">
        {{ collection.name }}
      </option>
    </select>
    <select
      v-if="selected_collection_id !== null"
      v-model="selected_collection_class"
      class="mr-2 h-8 w-32 rounded-md border-transparent py-0 pl-2 pr-8 text-sm text-gray-500 ring-1 ring-gray-300 focus:border-blue-500 focus:ring-blue-500">
      <option
        v-for="class_details in appState.collections[
          appState.collections.findIndex((e) => e.id == selected_collection_id)
        ]?.actual_classes"
        :value="class_details.name">
        {{ class_details.name == "_default" ? "Items" : class_details.name }}
      </option>
    </select>
  </div>
</template>

<style scoped></style>
