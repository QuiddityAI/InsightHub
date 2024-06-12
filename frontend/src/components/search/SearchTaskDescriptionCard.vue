<script setup>
import { useToast } from 'primevue/usetoast';
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
  emits: [],
  data() {
    return {
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
  },
}
</script>

<template>
  <div class="flex flex-col bg-white shadow-sm rounded-md p-6">
    <div class="flex flex-row items-center justify-between">
      <h3 class="text-sm text-gray-500">Quick Search</h3>
      <div class="flex flex-row items-center gap-2">
        <button class="py-1 px-2 rounded-md bg-gray-100 text-sm text-gray-500  hover:bg-blue-100/50 hover:text-gray-700"
          @click="eventBus.emit('edit-search-task-description')">
          Edit
        </button>
        <button class="py-1 px-2 rounded-md bg-gray-100 text-sm text-gray-500  hover:bg-blue-100/50 hover:text-gray-700"
          @click="appState.reset_search_results_and_map()">
          New Search
        </button>
      </div>
    </div>

    <div class="flex flex-row items-center justify-between">
      <h2 class="text-lg font-bold">{{ mapState.map_parameters?.search.all_field_query }}</h2>
    </div>
  </div>

</template>

<style scoped>
</style>
