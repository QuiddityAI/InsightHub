<script setup>
import {
  InformationCircleIcon,
} from "@heroicons/vue/24/outline"

import Chip from "primevue/chip"

import BorderlessButton from "../widgets/BorderlessButton.vue";

import RangeFilterList from "../search/RangeFilterList.vue";
import TextFilterInput from "./TextFilterInput.vue";

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
  <div class="w-full px-5 py-2 flex flex-col gap-1">

    <div class="flex flex-row items-center gap-4">
      <span class="flex-none text-gray-500"
        v-tooltip="{value: 'This only affects already existing items / results.\nTo apply a filter to the normal search, use the filters there.', showDelay: 400}">
        Filter existing items / search results
        <InformationCircleIcon class="h-4 w-4 inline text-blue-500">
        </InformationCircleIcon>:
      </span>

      <TextFilterInput></TextFilterInput>

    </div>

    <RangeFilterList></RangeFilterList>

    <div class="mt-2 flex flex-row flex-wrap gap-2 text-xs">
      <div v-for="filter in collectionStore.collection.filters" :key="filter.uid" class="flex items-center gap-1 bg-red-100 px-2 py-[2px] rounded-full">
        <span class="text-gray-500">{{ filter.display_name }}</span>
        <!-- don't use built-in 'removable' feature of Chip because it would remove the element even for future filter list -->
        <button v-if="filter.removable" @click="collectionStore.remove_filter(filter.uid)" v-tooltip="{value: 'Remove Filter', showDelay: 400}"
            class="ml-2 h-4 w-4 flex items-center justify-center rounded-full bg-white text-xs text-gray-500">X</button>
      </div>
    </div>

  </div>
</template>

<style scoped>
</style>
