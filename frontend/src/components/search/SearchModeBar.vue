<script setup>
import {
  PencilIcon,
  NoSymbolIcon,
} from "@heroicons/vue/24/outline"


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
  <div class="px-3 h-7 flex flex-row items-center gap-4 rounded border border-blue-500">
    <span class="text-blue-500">Search Mode:</span>
    <span class="text-gray-700" v-for="source in active_search_sources">
      {{ source.query }}
    </span>
    <div class="flex-1"></div>
    <BorderlessButton @click="$emit('edit_search_task')">
      <PencilIcon class="h-5 w-5 inline" /> Edit
    </BorderlessButton>
    <BorderlessButton @click="collectionStore.exit_search_mode">
      <NoSymbolIcon class="h-5 w-5 inline" /> Exit
    </BorderlessButton>
  </div>
</template>

<style scoped>
</style>
