<script setup>

import Message from 'primevue/message';

import CollectionList from "../collections/CollectionList.vue"
import CollectionView from "../collections/CollectionView.vue"
import CreateCollectionArea from './CreateCollectionArea.vue';

import { useToast } from 'primevue/usetoast';
import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const mapState = useMapStateStore()
const collectionStore = useCollectionStore()
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
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.eventBus.on("show_table", this.on_show_table)
  },
  unmounted() {
    this.eventBus.off("show_table", this.on_show_table)
  },
  watch: {
    'appStateStore.organization'(newVal, oldVal) {
      if (newVal) {
        this.collectionStore.get_available_collections(this.appStateStore.organization.id)
      }
    },
  },
  methods: {
    on_show_table({collection_id, class_name}) {
      this.collectionStore.open_collection(collection_id, class_name)
    },
  },
}
</script>

<template>
  <div class="overflow-hidden flex flex-row relative bg-gray-200">

    <!-- Left Side Bar -->
    <CollectionList
      class="absolute z-40">
    </CollectionList>

    <!-- placeholder for collection list (which is absolute positioned) -->
    <div class="min-w-[250px]" v-if="!collectionStore.collection"></div>

    <!-- Right Side Content -->
    <CollectionView v-if="collectionStore.collection"
      class="flex-1 h-full relative z-20">
    </CollectionView>

    <div v-else
      class="h-full w-full flex flex-col gap-5 items-center overflow-y-auto">
      <CreateCollectionArea
      ></CreateCollectionArea>
    </div>

  </div>

</template>

<style scoped>
</style>
