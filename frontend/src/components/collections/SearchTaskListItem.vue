<script setup>

import { useToast } from 'primevue/usetoast';

import SearchTaskExecutionSettings from '../search/SearchTaskExecutionSettings.vue';

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()
const toast = useToast()
</script>

<script>

export default {
  inject: [],
  props: ["task"],
  emits: [],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
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
  <div class="flex flex-col gap-2 border border-gray-200 p-3 rounded-lg">

    <button class="flex felx-row gap-2 hover:text-blue-500"
      v-tooltip.bottom="{value: 'Run this search task', showDelay: 400}"
      @click="collectionStore.run_existing_search_task(task.id)">
      {{ task.settings.user_input || 'Search Task' }}
    </button>

    <SearchTaskExecutionSettings :task="collectionStore.collection.most_recent_search_task">
    </SearchTaskExecutionSettings>

    </div>

</template>

<style scoped>
</style>
