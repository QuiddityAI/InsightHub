<script setup>
import { httpClient } from "../../api/httpClient"

import { EllipsisVerticalIcon, TrashIcon } from "@heroicons/vue/24/outline"

import CollectionClassListItem from "./CollectionClassListItem.vue"

import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
const appState = useAppStateStore()

</script>

<script>
export default {
  props: [],
  emits: ["collection_selected", "class_selected"],
  data() {
    return {}
  },
  computed: {
    ...mapStores(useAppStateStore),
  },
  mounted() {},
  methods: {
    create_collection(name) {
      if (!name) {
        return
      }
      const that = this
      const create_collection_body = {
        name: name,
        related_organization_id: this.appStateStore.organization.id,
      }
      httpClient
        .post("/org/data_map/add_collection", create_collection_body)
        .then(function (response) {
          // put the new collection at the beginning of the list
          that.appStateStore.collections.unshift(response.data)
          that.appStateStore.last_used_collection_id = response.data.id
          that.appStateStore.last_used_collection_class = response.data.actual_classes[0].name
        })
    },
  },
}
</script>

<template>
  <div>

    <div v-if="appState.logged_in" class="mt-2 mb-2 flex items-stretch">
      <input
        ref="new_collection_name"
        type="text"
        class="flex-auto rounded-l-md border-0 py-1.5 text-gray-900 ring-1 ring-inset ring-gray-200 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        placeholder="Collection Name"
        @keyup.enter="create_collection($refs.new_collection_name.value); $refs.new_collection_name.value = ''" />
      <button
        class="rounded-r-md border-0 px-2 py-1.5 text-gray-400 hover:text-blue-500 ring-1 ring-inset ring-gray-200 placeholder:text-gray-400 focus:ring-2 focus:ring-inset focus:ring-blue-400 sm:text-sm sm:leading-6"
        type="button"
        @click="create_collection($refs.new_collection_name.value); $refs.new_collection_name.value = ''">
        Create
      </button>
    </div>

    <ul v-if="Object.keys(appState.collections).length !== 0" role="list" class="mt-5">
      <li
        v-for="collection in appState.collections"
        :key="collection.id"
        class="mb-4 rounded-md bg-gray-100 pb-1 pl-3 pr-2 pt-2">

        <div class="flex flex-row gap-3">
          <span class="font-bold text-gray-600">{{ collection.name }}</span>
          <div class="flex-1"></div>
          <button
            @click="$emit('collection_selected', collection.id)"
            class="ml-1 w-8 rounded px-1 hover:bg-gray-100">
            <EllipsisVerticalIcon></EllipsisVerticalIcon>
          </button>
        </div>

        <ul class="mt-3">
          <CollectionClassListItem
            v-for="class_details in collection.actual_classes.slice(0, 3)"
            :key="class_details.name"
            :class_details="class_details"
            @click="$emit('class_selected', class_details.name); $emit('collection_selected', collection.id)">
          </CollectionClassListItem>
        </ul>

        <button
          v-if="collection.actual_classes.length > 3"
          class="mb-2 flex flex-row gap-3 py-[1px] pr-2"
          @click="$emit('collection_selected', collection.id)">
          <span class="text-sm pl-2 text-gray-500 hover:text-blue-500">
            Show all {{ collection.actual_classes.length }} classes
          </span>
        </button>
      </li>
    </ul>

    <div
      v-if="Object.keys(appState.collections).length === 0"
      class="flex h-20 flex-col place-content-center text-center">
      <p class="flex-none text-gray-400">No Collections Yet</p>
    </div>
  </div>
</template>
