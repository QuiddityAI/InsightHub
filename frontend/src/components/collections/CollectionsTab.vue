<script setup>

import Message from 'primevue/message';

import CollectionList from "../collections/CollectionList.vue"
import CollectionClassesList from "../collections/CollectionClassesList.vue"
import CollectionClassDetails from "../collections/CollectionClassDetails.vue"

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
      selected_collection: null,
      selected_collection_class: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("show_table", ({collection_id, class_name}) => {
      this.selected_collection = collection_id
      this.selected_collection_class = class_name
    })
  },
  watch: {
  },
  methods: {
    open_collection(collection_id, class_name) {
      if (this.selected_collection) {
        this.close_collection()
        setTimeout(() => {
          this.selected_collection = collection_id
          this.selected_collection_class = class_name
        }, 0)
      } else {
        this.selected_collection = collection_id
        this.selected_collection_class = class_name
      }
    },
    close_collection() {
      this.selected_collection = null
      this.selected_collection_class = null
    },
  },
}
</script>

<template>
  <div class="overflow-hidden flex flex-row relative">

    <!-- Left Side Bar -->
    <CollectionList
      class="z-40"
      :collapsed="selected_collection && selected_collection_class"
      :selected_collection="selected_collection"
      :selected_collection_class="selected_collection_class"
      @collection_selected="open_collection"
      @open_new_collection_dialog="close_collection">
    </CollectionList>

    <!-- Right Side Content -->
    <div v-if="!appState.logged_in"
      class="h-full flex flex-row gap-5 items-center justify-center">
      <Message :closable="false">
        Log in to save items in collections and extract information in a table
      </Message>
    </div>

    <CollectionClassDetails v-else-if="selected_collection && selected_collection_class"
      class="flex-1 h-full relative z-20"
      :collection_id="selected_collection"
      :class_name="selected_collection_class"
      @close="close_collection">
    </CollectionClassDetails>

    <div v-else
      class="h-full w-full flex flex-col gap-5 justify-center">
      <Message :closable="false">
        Select a collection to view its classes
      </Message>
    </div>

  </div>

</template>

<style scoped>
</style>
