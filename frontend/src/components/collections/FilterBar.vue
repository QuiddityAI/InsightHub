<script setup>
import {
  PencilIcon,
  NoSymbolIcon,
} from "@heroicons/vue/24/outline"

import Chip from "primevue/chip"


import BorderlessButton from "../widgets/BorderlessButton.vue";

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
      <span class="flex-none text-gray-500">Visibility Filters:</span>

      <div class="flex flex-col gap-2 text-xs">
        <Chip v-for="filter in collectionStore.collection.filters" :key="filter.uid">
          <span class="text-gray-500">{{ filter.display_name }}</span>
          <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for future filter list -->
          <button v-if="filter.removable" @click="collectionStore.remove_filter(filter.uid)" v-tooltip="{value: 'Remove Filter', showDelay: 400}"
              class="ml-2 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
        </Chip>
      </div>

    </div>
  </div>
</template>

<style scoped>
</style>
