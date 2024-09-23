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
      currently_selected_collection: null,
      currently_selected_collection_class: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
  },
  mounted() {
    this.eventBus.on("show_table", ({collection_id, class_name}) => {
      this.currently_selected_collection = collection_id
      this.currently_selected_collection_class = class_name
    })
  },
  watch: {
  },
  methods: {
  },
}
</script>

<template>
  <div class="mt-1 pt-4 pb-3 px-5 shadow-sm rounded-md bg-white overflow-hidden">

    <div v-if="!appState.logged_in" class="h-full flex flex-row gap-5 items-center justify-center">
      <Message :closable="false">
        Log in to save items in collections and extract information in a table
      </Message>
    </div>

    <div v-if="appState.logged_in" class="h-full flex flex-row gap-5 items-center justify-center">

      <CollectionList
        v-if="!currently_selected_collection && !currently_selected_collection_class"
        class="w-[500px] h-full overflow-y-auto"
        @collection_selected="(collection_id) => currently_selected_collection = collection_id"
        @class_selected="(class_name) => currently_selected_collection_class = class_name">
      </CollectionList>

      <CollectionClassesList
        v-if="currently_selected_collection && !currently_selected_collection_class"
        class="w-[500px] h-full overflow-y-auto"
        :collection_id="currently_selected_collection"
        @class_selected="(class_name) => currently_selected_collection_class = class_name"
        @close="currently_selected_collection = null">
      </CollectionClassesList>

      <CollectionClassDetails
        v-if="currently_selected_collection && currently_selected_collection_class"
        class="flex-1 h-full"
        :collection_id="currently_selected_collection"
        :class_name="currently_selected_collection_class"
        @close="currently_selected_collection = null; currently_selected_collection_class = null">
      </CollectionClassDetails>

    </div>

  </div>

</template>

<style scoped>
</style>
