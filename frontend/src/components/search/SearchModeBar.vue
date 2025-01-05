<script setup>
import {
  PencilIcon,
  NoSymbolIcon,
  ChevronUpIcon,
} from "@heroicons/vue/24/outline"


import BorderlessButton from "../widgets/BorderlessButton.vue";
import SearchFilterList from "./SearchFilterList.vue";

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from '../../stores/collection_store';
import { httpClient } from "../../api/httpClient"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()

</script>

<script>

export default {
  inject: ["eventBus"],
  props: [],
  emits: ["edit_search_task"],
  data() {
    return {
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    active_search_sources() {
      return this.collectionStore.collection.search_sources.filter((source) => source.is_active)
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
  <div class="w-full px-5 py-1 flex flex-col gap-1">
    <div class="flex flex-row items-center gap-4">

      <BorderlessButton v-if="collectionStore.collection.search_tasks.length >= 2 && !collectionStore.collection.search_tasks.at(-2).exit_search_mode"
        @click="collectionStore.run_previous_search_task"
        v-tooltip.bottom="{value: 'Go to the previous search result', showDelay: 400}"
        class="h-full -mr-3 -ml-3">
        <ChevronUpIcon class="h-5 w-5" />
      </BorderlessButton>

      <span class="flex-none text-blue-500">Search Mode:</span>

      <div class="flex flex-col gap-2">
        <div v-for="source in active_search_sources" :key="source.id">
          <span class="text-gray-700">
            {{ source.query }}
          </span>
          <SearchFilterList v-for="source in active_search_sources"
            :filters="source.filters || []" :key="source.id"
            :removable="false"
            class="-ml-1 mt-1 mb-1">
          </SearchFilterList>
        </div>
      </div>

      <div class="flex-1"></div>

      <BorderlessButton @click="$emit('edit_search_task')" class="py-1"
        v-tooltip.bottom="{value: 'Edit the search query and filters', showDelay: 400}">
        <PencilIcon class="h-5 w-5 inline" /> Edit
      </BorderlessButton>
      <BorderlessButton @click="collectionStore.exit_search_mode" class="py-1"
        v-tooltip.bottom="{value: 'Remove search results and show saved items', showDelay: 400}">
        <NoSymbolIcon class="h-5 w-5 inline" /> Exit
      </BorderlessButton>
    </div>
  </div>
</template>

<style scoped>
</style>
