<script setup>

import { useToast } from 'primevue/usetoast';

import SearchTaskListItem from './SearchTaskListItem.vue';

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
  props: [],
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
    this.collectionStore.fetch_saved_search_tasks()
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="flex flex-col gap-5 px-10">
    <div class="flex flex-row items-center gap-3">
      <h3 class="font-bold text-[15px]">
        Saved / Periodic Searches
      </h3>
    </div>

    <ul class="flex flex-col gap-5">
      <SearchTaskListItem v-for="task in collectionStore.saved_search_tasks"
        :task="task">
      </SearchTaskListItem>
    </ul>

    <div v-if="collectionStore.saved_search_tasks.length === 0">
      <div class="text-gray-400 ml-3 -mt-3">
        No saved searches yet
      </div>
    </div>
  </div>

</template>

<style scoped>
</style>
