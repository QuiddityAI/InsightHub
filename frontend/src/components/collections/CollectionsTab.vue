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
    this.eventBus.on("show_table", ({collection_id, class_name}) => {
      this.collectionStore.open_collection(collection_id, class_name)
    })
  },
  watch: {
    'appStateStore.organization'(newVal, oldVal) {
      if (newVal) {
        this.collectionStore.get_available_collections(this.appStateStore.organization.id)
      }
    },
  },
  methods: {
  },
}
</script>

<template>
  <div class="overflow-hidden flex flex-row relative">

    <!-- Left Side Bar -->
    <CollectionList
      class="z-40">
    </CollectionList>

    <!-- Right Side Content -->
    <div v-if="!appState.logged_in"
      class="h-full flex flex-row gap-5 items-center justify-center">
      <Message :closable="false">
        Log in to save items in collections and extract information in a table
      </Message>
    </div>

    <CollectionView v-else-if="collectionStore.collection"
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
