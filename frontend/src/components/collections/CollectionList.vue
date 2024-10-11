<script setup>

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useCollectionStore } from "../../stores/collection_store"

const appState = useAppStateStore()
const collectionStore = useCollectionStore()

</script>

<script>
export default {
  props: [],
  emits: [],
  data() {
    return {}
  },
  computed: {
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
    collapsed() {
      return this.collectionStore.collection_id !== null
    },
  },
  mounted() {},
  methods: {
    open_new_collection_dialog() {
      this.collectionStore.close_collection()
    },
  },
}
</script>

<template>
  <div class="h-full w-[250px] transition-[margin] duration-300 shadow-md bg-white"
    :class="{
      '-ml-[250px]': collapsed,
      'ml-0': !collapsed,
    }">

    <div
      class="h-full overflow-y-auto flex flex-col gap-3 pt-6 pb-3 pl-3 pr-3">

      <div class="flex flex-row items-center text-left px-2">
        <h3 class="font-bold text-[15px]">
          Recent Collections
        </h3>
      </div>

      <div v-for="collection in collectionStore.available_collections" :key="collection.id"
        class="flex flex-row">
        <button class="w-full text-left text-[15px] text-md px-2 py-1 flex flex-row items-center rounded-md hover:text-blue-500 hover:bg-gray-100"
          @click="collectionStore.open_collection(collection.id, collection.actual_classes[0].name)">
          <h3>
            {{ collection.name }}
          </h3>
        </button>
      </div>

    </div>
  </div>
</template>
