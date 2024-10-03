<script setup>
import {
  AdjustmentsHorizontalIcon,
  MinusCircleIcon,
  HomeIcon,
  ClockIcon,
  BookmarkIcon,
  MagnifyingGlassIcon,
  ChatBubbleLeftIcon,
  PaperAirplaneIcon,
  UserCircleIcon,
} from "@heroicons/vue/24/outline"

import { useToast } from 'primevue/usetoast';
import OverlayPanel from 'primevue/overlaypanel';

import { httpClient, djangoClient } from "../../api/httpClient"
import { mapStores } from "pinia"
import { useAppStateStore } from "../../stores/app_state_store"
import { useMapStateStore } from "../../stores/map_state_store"
import { useCollectionStore } from "../../stores/collection_store";

import UserMenu from "../search/UserMenu.vue";
import LoginButton from "../general/LoginButton.vue";

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
      internal_organization_id: null,
    }
  },
  computed: {
    ...mapStores(useMapStateStore),
    ...mapStores(useAppStateStore),
    ...mapStores(useCollectionStore),
  },
  mounted() {
    this.internal_organization_id = this.appStateStore.organization_id
  },
  watch: {
    "appStateStore.organization_id": function (newValue, oldValue) {
      // using internal variable to be able to reset parameters before
      // actually changing global dataset_id in select-field listener below
      this.internal_organization_id = this.appStateStore.organization_id
    },
  },
  methods: {
    organization_id_changed_by_user() {
      this.appStateStore.set_organization_id(this.internal_organization_id)
    },
  },
}
</script>


<template>

  <div class="flex flex-col p-1 bg-white shadow-sm">

    <div class="flex-none flex flex-row items-center justify-center mx-3">

      <a
        v-tooltip.right="{ value: 'Reset search', showDelay: 400 }"
        :href="`?organization_id=${appState.organization_id}`"
        class="w-8 rounded p-2 text-gray-400 hover:bg-gray-100">
        <HomeIcon></HomeIcon>
      </a>

      <div class="ml-1 flex-initial"
        v-tooltip.bottom="{ value: 'Select the organization', showDelay: 400 }">
        <select
          v-model="internal_organization_id"
          @change="organization_id_changed_by_user"
          class="w-full rounded-md border-transparent pb-1 pl-2 pr-8 pt-1 text-sm text-gray-500">
          <option v-for="item in appState.available_organizations" :value="item.id" selected>
            {{ item.name }}
          </option>
        </select>
      </div>

      <div class="flex-1"></div>

      <div class="hidden md:flex flex-row gap-4 lg:gap-8 text-gray-500 text-sm">
        <!-- <button class="hover:text-blue-500" :class="{'text-blue-500': appState.selected_app_tab === 'explore'}"
          @click="appState.set_app_tab('explore')">
          Explore</button> -->
         <button class="hover:text-blue-500" :class="{'font-bold': appState.selected_app_tab === 'collections'}"
          @click="appState.set_app_tab('collections'); collectionStore.close_collection()">
          Home</button>
         <!-- <button class="hover:text-blue-500" :class="{'text-blue-500': appState.selected_app_tab === 'chats'}"
          v-if="appState.user?.is_staff"
          @click="appState.set_app_tab('chats')">
          Chat</button>
         <button class="hover:text-blue-500" :class="{'text-blue-500': appState.selected_app_tab === 'write'}"
          v-if="appState.user?.is_staff"
          @click="appState.set_app_tab('write')">
          Write</button> -->
         <button class="hover:text-blue-500" :class="{'font-bold': appState.selected_app_tab === 'datasets'}"
          @click="appState.set_app_tab('datasets')">
          Upload Files</button>
      </div>

      <div class="flex-1"></div>

      <!-- wrapping login area in div to make it roughly the same width as organization dropdown -->
      <div class="flex-none flex flex-row place-content-end w-min-0 w-48">
        <LoginButton></LoginButton>

        <button v-if="appState.logged_in" class="pl-2 pr-1 py-1 text-sm text-gray-500 rounded-md hover:bg-gray-100"
          v-tooltip.bottom="{ value: 'User Menu (logout etc.)', showDelay: 400 }"
          @click="(event) => $refs.user_menu.toggle(event)">
          {{ appState.user.username.substring(0, 22) + (appState.user.username.length > 22 ? '...' : '') }}
          <UserCircleIcon class="inline-block w-5 h-5 pb-1 ml-2"></UserCircleIcon>
        </button>

        <OverlayPanel ref="user_menu">
          <UserMenu @hide="$refs.user_menu.hide()"></UserMenu>
        </OverlayPanel>
      </div>

    </div>

    <div class="flex flex-row items-center justify-center">
      <select class="md:hidden rounded-md border-transparent pb-1 pl-2 pr-8 pt-1 text-sm font-['Lexend'] font-bold text-black">
        <!-- <option>Explore</option> -->
        <option>Home</option>
        <!-- <option>Chat</option>
        <option v-if="appState.user?.is_staff">Write</option> -->
        <option>Upload Files</option>
      </select>
    </div>

  </div>

</template>

<style scoped>
</style>